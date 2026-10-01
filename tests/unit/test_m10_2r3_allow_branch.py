"""M10.2-R.3 — the internal↔external ALLOW branch, on a deterministic fixture.

Every earlier exercise of the seven-dimension test across the domain boundary **rejected**,
and rejection alone does not show the check works — a function that always returns
`INCOMPATIBLE` would pass every one of those tests. What was missing is the other half:
that a genuinely comparable internal calculation and external sourced statement reach
`COMPATIBLE`, through the real production path, with nothing forced.

**The evidence here is synthetic and is not a real external source.** `Synthetic Logistics
Ltd` is not a company, `synthetic-source.example.invalid` is a reserved host that can never
resolve, and the figures are invented for this test. Nothing in this module may be read as
a real-world observation, and nothing in it reaches a network.

The pair is truthful in the sense that matters: the external statement genuinely describes
**the same metric, of the same entity, over the same period, on the same basis** as the
internal calculation — a filed-account restatement of a company's own revenue, which is the
one shape where an internal↔external monetary comparison is legitimate. It is deliberately
*not* revenue against a market size, which must never compare.

The external side arrives in the source's own notation, `GBP 12.5 million`, and is
canonicalised at construction (ADR-0025). `compatibility.compare()` is unmodified, converts
nothing, and never sees a magnitude-qualified label.
"""

import json
import os
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import jsonschema_mini                            # noqa: E402
from bops import materiality as materiality_mod             # noqa: E402
from bops import quantity as Q                              # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.analytics import contract as analytics_contract   # noqa: E402
from bops.kpi import contract as kpi_contract               # noqa: E402
from bops.research import evidence_set as evidence_mod      # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402

SCHEMA_PATH = os.path.join(REPO_ROOT, "lib", "schemas", "synthesis.schema.json")

# -- the fixture's semantics, stated once ------------------------------------
#
# Both sides carry these verbatim. They are equal because the two statements genuinely
# describe one quantity, not because anything normalised them into agreement.

COMPANY = "Synthetic Logistics Ltd"
DEFINITION = ("net revenue recognised from sales transactions, after trade discount and "
              "before VAT")
PERIOD = "FY2025 (calendar-year equivalent)"
GEOGRAPHY = "United Kingdom"
CURRENCY = "GBP"
SCOPE = "total revenue of %s" % COMPANY
METHODOLOGY = "sum of transaction net revenue during FY2025"

#: The canonical quantity both sides must land on, in base units.
CANONICAL = Decimal("12500000")

#: What the synthetic source published, in its own notation.
SOURCE_VALUE = Decimal("12.5")
SOURCE_NOTATION = "GBP million"
SOURCE_TEXT = ("Filed accounts for %s state net revenue of GBP 12.5 million for FY2025, "
               "after trade discount and before VAT." % COMPANY)

DATASET_ID = "ds-synthetic-logistics"

#: The dimensions the external statement carries. `unit` and `currency` are absent on
#: purpose: they are produced by canonicalising the source's notation, not asserted.
EXTERNAL_DIMENSIONS = {
    "metric_definition": DEFINITION,
    "period": PERIOD,
    "geography": GEOGRAPHY,
    "scope": SCOPE,
    "methodology": METHODOLOGY,
}


def internal_analysis():
    """One synthetic internal analysis holding a single revenue calculation."""
    analysis = analytics_contract.AnalysisSet(
        "financial", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "synthetic_logistics_fy2025.csv"})
    analysis.add(analytics_contract.AnalysisFinding(
        "financial.kpi.revenue", "financial", analytics_contract.CALCULATION,
        "Revenue for FY2025 was GBP 12,500,000.",
        metric="revenue", period=PERIOD, observed=CANONICAL,
        unit=kpi_contract.CURRENCY, currency=CURRENCY, basis="sum(net_revenue)",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Revenue is the reported headline figure for the period."))
    return analysis


def synthetic_evidence(host="synthetic-source.example.invalid", tier="C"):
    """One synthetic external evidence item on a reserved host. Never a real source."""
    return evidence_mod.EvidenceItem(
        source="SYNTHETIC Filing Archive (test fixture, not a real source)",
        reference="https://%s/filings/synthetic-logistics-fy2025" % host,
        source_tier=tier, retrieved_at="2026-09-15", publication_date="2026-04-30",
        source_type=evidence_mod.RESEARCH_HOUSE, content=SOURCE_TEXT,
        claim_kind="financials", as_of="2026-09-15")


def build_pair(external_overrides=None, source_value=SOURCE_VALUE,
               source_notation=SOURCE_NOTATION):
    """The production path, end to end. Returns `(set, internal, external, evidence)`.

    Nothing here bypasses a public interface: the internal statement arrives through
    `from_analysis_set`, the evidence through `register_external`, and the external
    statement through `sourced_statement` with the source's own notation.
    """
    result = S.SynthesisSet(subject="M10.2-R.3 deterministic ALLOW fixture",
                            currency=CURRENCY)
    result.register_dataset(DATASET_ID, label="synthetic_logistics_fy2025.csv")

    produced = S.from_analysis_set(
        result, internal_analysis(), S.ORIGIN_FINANCIAL, dataset_id=DATASET_ID,
        metric_definition=DEFINITION, geography=GEOGRAPHY, scope=SCOPE,
        methodology=METHODOLOGY)
    internal = [item for item in produced if item.metric == "revenue"][0]

    evidence = synthetic_evidence()
    S.register_external(result, _set_of(evidence), S.ORIGIN_COMPANY)

    dimensions = dict(EXTERNAL_DIMENSIONS)
    dimensions.update(external_overrides or {})
    external = S.sourced_statement(
        result, S.ORIGIN_COMPANY, SOURCE_TEXT, evidence_ids=[evidence.id],
        metric="revenue", observed=source_value, source_unit=source_notation,
        **dimensions)
    return result, internal, external, evidence


def _set_of(*items):
    evidence_set = evidence_mod.EvidenceSet(
        operation="op-m10-2r3-synthetic", subject=COMPANY, category="company",
        disclosure_tier=0)
    for item in items:
        evidence_set.add(item)
    return evidence_set


# -- 1. the ALLOW branch -----------------------------------------------------

class SevenDimensionAllow(unittest.TestCase):
    """The branch every earlier cross-domain exercise failed to reach."""

    def setUp(self):
        self.result, self.internal, self.external, self.evidence = build_pair()

    def test_1_all_seven_dimensions_are_compatible(self):
        comparison = S.compare(self.internal, self.external)
        self.assertEqual(comparison["status"], S.COMPATIBLE)
        self.assertEqual(sorted(comparison["matched"]), sorted(S.DIMENSIONS))
        self.assertEqual(comparison["mismatched"], [])
        self.assertEqual(comparison["unknown"], [],
                         "an unknown dimension must never reach ALLOW")
        self.assertEqual(len(comparison["matched"]), 7)

    def test_1b_every_dimension_is_stated_on_both_sides(self):
        for dimension in S.DIMENSIONS:
            self.assertIsNotNone(self.internal.dimensions[dimension], dimension)
            self.assertIsNotNone(self.external.dimensions[dimension], dimension)

    def test_2_may_combine_is_true(self):
        self.assertTrue(S.may_combine(S.compare(self.internal, self.external)))

    def test_3_the_production_path_reaches_allow_through_compare_values(self):
        """`compare_values` is the sanctioned entry point; it must agree with `compare`."""
        outcome = S.compare_values(self.result, self.internal, self.external,
                                   subject="FY2025 revenue, internal vs filed")
        self.assertEqual(outcome["status"], S.COMPATIBLE)
        self.assertTrue(S.may_combine(outcome))

    def test_4_converted_is_false_and_nothing_converts(self):
        comparison = S.compare(self.internal, self.external)
        self.assertFalse(comparison["converted"])
        self.assertTrue(S.NEVER_CONVERTS)

    def test_5_no_fx_mechanism_exists_on_the_path(self):
        for module_path in (("lib", "python", "bops", "synthesis", "compatibility.py"),
                            ("lib", "python", "bops", "quantity.py")):
            with open(os.path.join(REPO_ROOT, *module_path),
                      encoding="utf-8") as handle:
                source = handle.read().lower()
            for forbidden in ("exchange_rate", "fx_rate", "rate_table",
                              "convert_currency"):
                self.assertNotIn(forbidden + " =", source)
        self.assertFalse(hasattr(Q, "convert_currency"))

    def test_6_no_combined_figure_is_produced(self):
        """Comparability is a precondition, not permission to do arithmetic in passing."""
        comparison = S.compare(self.internal, self.external)
        for absent in ("ratio", "difference", "share", "midpoint", "combined", "value"):
            self.assertNotIn(absent, comparison)

    def test_7_units_and_values_are_canonical_before_comparison(self):
        self.assertEqual(self.internal.unit, kpi_contract.CURRENCY)
        self.assertEqual(self.external.unit, kpi_contract.CURRENCY)
        self.assertEqual(self.internal.currency, CURRENCY)
        self.assertEqual(self.external.currency, CURRENCY)
        self.assertEqual(self.internal.observed, CANONICAL)
        self.assertEqual(self.external.observed, CANONICAL)


# -- 2. scale normalisation --------------------------------------------------

class ScaleNormalisation(unittest.TestCase):

    def test_8_gbp_12_point_5_million_canonicalises(self):
        amount, quantity_type, currency = Q.canonical_amount(
            Decimal("12.5"), unit_text="GBP million")
        self.assertEqual(amount, CANONICAL)
        self.assertEqual(str(amount), "12500000")
        self.assertEqual(quantity_type, kpi_contract.CURRENCY)
        self.assertEqual(currency, CURRENCY)

    def test_9_gbp_12_500_000_canonicalises_identically(self):
        amount, quantity_type, currency = Q.canonical_amount(
            Decimal("12500000"), unit_text="GBP")
        self.assertEqual(amount, CANONICAL)
        self.assertEqual(str(amount), "12500000")
        self.assertEqual(quantity_type, kpi_contract.CURRENCY)
        self.assertEqual(currency, CURRENCY)

    def test_10_both_notations_compare_compatibly(self):
        _r, _i, from_millions, _e = build_pair()
        result, _i2, from_units, _e2 = build_pair(
            source_value=Decimal("12500000"), source_notation="GBP")
        self.assertEqual(from_millions.observed, from_units.observed)
        self.assertEqual(from_millions.unit, from_units.unit)
        self.assertEqual(from_millions.currency, from_units.currency)
        self.assertEqual(S.compare(from_millions, from_units)["status"], S.COMPATIBLE)

    def test_11_no_floating_point_drift(self):
        with self.assertRaises(Q.QuantityError):
            Q.canonical_amount(12.5, unit_text="GBP million")
        amount, _t, _c = Q.canonical_amount(Decimal("0.1"), unit_text="GBP million")
        self.assertEqual(amount, Decimal("100000"))

    def test_12_the_sources_own_notation_stays_auditable(self):
        """Canonicalising the statement must not erase what the source actually wrote."""
        _result, _internal, _external, evidence = build_pair()
        self.assertIn("GBP 12.5 million", evidence.content)
        # The item is constructed directly, as the existing synthesis fixtures do, so it
        # carries no pipeline notes; `trust` is set by the type itself and is what marks
        # the content as data rather than instruction.
        self.assertEqual(evidence.trust, S.UNTRUSTED)

    def test_13_normalisation_happens_outside_compare(self):
        with open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                               "compatibility.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("import quantity", source)
        self.assertNotIn("quantity_mod", source)
        self.assertNotIn("SCALES", source)
        self.assertNotIn("canonical_amount", source)
        self.assertNotIn("scale_factor", source)


# -- 3. provenance and trust -------------------------------------------------

class ProvenanceAndTrustBoundary(unittest.TestCase):

    def setUp(self):
        self.result, self.internal, self.external, self.evidence = build_pair()

    def test_14_internal_stays_internal_and_internally_footed(self):
        self.assertEqual(self.internal.kind, sc.CALCULATION)
        self.assertEqual(self.internal.domain, S.INTERNAL)
        internal_refs = [r for r in self.internal.internal_refs()
                         if self.result.resolve_ref(r) is not None]
        self.assertTrue(internal_refs, "must rest on a registered internal object")
        self.assertIn(sc.P_DATASET, [r.kind for r in self.internal.provenance])

    def test_15_external_stays_external_sourced_and_untrusted(self):
        self.assertEqual(self.external.kind, sc.SOURCED)
        self.assertEqual(self.external.domain, S.EXTERNAL)
        self.assertEqual(self.external.trust, S.UNTRUSTED)
        stored = self.result.resolve_ref(
            sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id))
        self.assertIsNotNone(stored)
        self.assertEqual(stored.trust, S.UNTRUSTED)

    def test_16_allow_does_not_promote_the_external_statement(self):
        S.compare_values(self.result, self.internal, self.external, subject="revenue")
        self.assertEqual(self.external.kind, sc.SOURCED)
        self.assertEqual(self.external.trust, S.UNTRUSTED)
        self.assertEqual(self.internal.kind, sc.CALCULATION)
        self.assertEqual(self.result.recommendations, [])

    def test_17_provenance_resolves_on_both_sides(self):
        for item in (self.internal, self.external):
            self.assertTrue(item.provenance)
            for ref in item.provenance:
                if ref.is_resolvable:
                    self.assertIsNotNone(self.result.resolve_ref(ref),
                                         "%s did not resolve" % (ref.key(),))


# -- 4. negative controls ----------------------------------------------------

class NegativeControls(unittest.TestCase):
    """The branch must not be reachable by anything that merely resembles the pair."""

    def _rejects(self, **overrides):
        source_value = overrides.pop("source_value", SOURCE_VALUE)
        source_notation = overrides.pop("source_notation", SOURCE_NOTATION)
        _result, internal, external, _e = build_pair(
            external_overrides=overrides, source_value=source_value,
            source_notation=source_notation)
        comparison = S.compare(internal, external)
        self.assertNotEqual(comparison["status"], S.COMPATIBLE)
        self.assertFalse(S.may_combine(comparison))
        return comparison

    def test_18_gbp_versus_usd_rejects(self):
        comparison = self._rejects(source_notation="USD million")
        self.assertIn("currency", [m["dimension"] for m in comparison["mismatched"]])

    def test_19_currency_versus_percent_rejects(self):
        result, internal, _external, evidence = build_pair()
        rate = S.sourced_statement(
            result, S.ORIGIN_COMPANY, "A synthetic source states a margin rate.",
            evidence_ids=[evidence.id], metric="revenue", observed=Decimal("34.9"),
            unit=kpi_contract.PERCENT, currency=CURRENCY, **EXTERNAL_DIMENSIONS)
        comparison = S.compare(internal, rate)
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        self.assertIn("unit", [m["dimension"] for m in comparison["mismatched"]])

    def test_20_revenue_versus_market_size_definition_rejects(self):
        comparison = self._rejects(
            metric_definition="total industry revenue across all participants")
        self.assertIn("metric_definition",
                      [m["dimension"] for m in comparison["mismatched"]])

    def test_21_uk_versus_global_rejects(self):
        comparison = self._rejects(geography="Global")
        self.assertIn("geography", [m["dimension"] for m in comparison["mismatched"]])

    def test_22_fy2025_versus_fy2026_rejects(self):
        comparison = self._rejects(period="FY2026 (calendar-year equivalent)")
        self.assertIn("period", [m["dimension"] for m in comparison["mismatched"]])

    def test_23_company_versus_industry_scope_rejects(self):
        comparison = self._rejects(scope="total revenue of the UK logistics industry")
        self.assertIn("scope", [m["dimension"] for m in comparison["mismatched"]])

    def test_24_different_methodology_rejects(self):
        comparison = self._rejects(
            methodology="top-down estimate from sector employment data")
        self.assertIn("methodology", [m["dimension"] for m in comparison["mismatched"]])

    def test_25_unknown_unit_rejects(self):
        result, internal, _e, evidence = build_pair()
        no_unit = S.sourced_statement(
            result, S.ORIGIN_COMPANY, "A synthetic source states a figure, no unit.",
            evidence_ids=[evidence.id], metric="revenue", observed=CANONICAL,
            currency=CURRENCY, **EXTERNAL_DIMENSIONS)
        comparison = S.compare(internal, no_unit)
        self.assertEqual(comparison["status"], S.UNKNOWN)
        self.assertIn("unit", [u["dimension"] for u in comparison["unknown"]])
        self.assertFalse(S.may_combine(comparison))

    def test_26_unknown_currency_rejects(self):
        """A source writing a bare scale establishes no currency, so the pair rejects."""
        result, internal, _e, evidence = build_pair()
        no_currency = S.sourced_statement(
            result, S.ORIGIN_COMPANY, "A synthetic source writes '12.5 million'.",
            evidence_ids=[evidence.id], metric="revenue", observed=SOURCE_VALUE,
            source_unit="million", **EXTERNAL_DIMENSIONS)
        self.assertIsNone(no_currency.currency)
        self.assertEqual(no_currency.unit, kpi_contract.CURRENCY)
        comparison = S.compare(internal, no_currency)
        self.assertEqual(comparison["status"], S.UNKNOWN)
        self.assertIn("currency", [u["dimension"] for u in comparison["unknown"]])

    def test_27_an_out_of_vocabulary_unit_cannot_be_asserted(self):
        result, _i, _e, evidence = build_pair()
        with self.assertRaises(S.SynthesisError):
            S.sourced_statement(result, S.ORIGIN_COMPANY, "x",
                                evidence_ids=[evidence.id], unit="GBP million")


# -- 5. compatibility is not value equality ----------------------------------

class CompatibilityIsNotValueEquality(unittest.TestCase):
    """The distinction this architecture draws deliberately, recorded as behaviour.

    `compare()` answers *may these two figures be related at all*. It reads the seven
    dimensions and **never reads a value** — there is no `observed` in the module. So a pair
    that is compatible on all seven dimensions while stating materially different numbers
    comes back `COMPATIBLE`, and that is not a defect: the two figures genuinely measure the
    same quantity, and the fact that they disagree about it is a *different* finding, for a
    layer that deliberately does not exist yet.

    These tests pin that boundary so a future milestone changes it on purpose rather than by
    accident.
    """

    def setUp(self):
        self.result, self.internal, self.external, _e = build_pair(
            source_value=Decimal("18.9"))          # GBP 18.9m vs the internal GBP 12.5m

    def test_28_unequal_values_are_not_made_equal_by_normalisation(self):
        self.assertEqual(self.internal.observed, Decimal("12500000"))
        self.assertEqual(self.external.observed, Decimal("18900000"))
        self.assertNotEqual(self.internal.observed, self.external.observed)

    def test_29_dimension_compatibility_is_independent_of_value_equality(self):
        comparison = S.compare(self.internal, self.external)
        self.assertEqual(comparison["status"], S.COMPATIBLE)

    def test_30_compare_never_reads_a_value(self):
        with open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                               "compatibility.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("observed", source)
        self.assertNotIn(".comparison", source)

    def test_31_no_value_conflict_is_recorded_for_a_compatible_pair(self):
        """`compare_values` returns early on COMPATIBLE: no conflict, no limitation.

        Documented, not asserted as desirable. A value-disagreement finding for a
        comparable pair is genuinely absent from this architecture today.
        """
        before_conflicts = len(self.result.conflicts)
        before_limitations = len(self.result.limitations)
        outcome = S.compare_values(self.result, self.internal, self.external,
                                   subject="FY2025 revenue")
        self.assertEqual(outcome["status"], S.COMPATIBLE)
        self.assertEqual(len(self.result.conflicts), before_conflicts)
        self.assertEqual(len(self.result.limitations), before_limitations)

    def test_32_nothing_is_averaged_and_both_positions_survive(self):
        S.compare_values(self.result, self.internal, self.external, subject="revenue")
        self.assertEqual(self.internal.observed, Decimal("12500000"))
        self.assertEqual(self.external.observed, Decimal("18900000"))
        midpoint = (Decimal("12500000") + Decimal("18900000")) / 2
        serialised = self.result.to_json()
        self.assertNotIn(str(midpoint), serialised)

    def test_33_an_incompatible_pair_still_records_a_conflict(self):
        """The contrast: where the pair is *not* comparable, the conflict layer fires."""
        result, internal, external, _e = build_pair(
            external_overrides={"geography": "Global"}, source_value=Decimal("18.9"))
        S.compare_values(result, internal, external, subject="revenue")
        cross = [c for c in result.conflicts if c.kind == S.INTERNAL_EXTERNAL]
        self.assertTrue(cross)
        self.assertTrue(cross[0].unresolved)
        values = sorted(str(v) for v in cross[0].values())
        self.assertEqual(values, sorted(["12500000", "18900000"]))


# -- 6. support, confidence and trust ----------------------------------------

class SupportAndConfidence(unittest.TestCase):

    def setUp(self):
        self.result, self.internal, self.external, self.evidence = build_pair()

    def test_34_the_synthetic_source_is_tiered_locally_as_c(self):
        """A reserved `.invalid` host is on no recognised list, so policy assigns tier C."""
        from bops.research import sources as sources_mod
        stored = self.result.resolve_ref(
            sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id))
        self.assertEqual(stored.source_tier, "C")
        # The tier is not taken on trust: registration re-derives it from the reference
        # and refuses anything stronger (see test_45). A reserved `.invalid` host is on no
        # recognised list, so local classification is C and the carried tier matches.
        local, basis, inferred = sources_mod.classify_tier(stored.reference, stored.source)
        self.assertEqual(local, "C")
        self.assertTrue(inferred)
        self.assertIn("not on the recognised A or B lists", basis)

    def test_35_tier_c_only_means_partially_supported(self):
        self.assertEqual(self.external.support, S.PARTIALLY_SUPPORTED)
        self.assertEqual(self.internal.support, S.SUPPORTED)

    def test_36_allow_does_not_raise_support_or_verify_anything(self):
        before = (self.external.support, self.external.confidence)
        S.compare_values(self.result, self.internal, self.external, subject="revenue")
        self.assertEqual((self.external.support, self.external.confidence), before)
        self.assertEqual(self.result.candidate_claims, [])

    def test_37_confidence_stays_qualitative(self):
        assessment = self.external.confidence_detail
        self.assertIn(self.external.confidence, (S.HIGH, S.MEDIUM, S.LOW))
        self.assertIn("Not a probability", assessment["basis"])
        self.assertFalse(assessment["statistical_interval"])
        for value in assessment.values():
            self.assertNotIsInstance(value, float)


# -- 7. serialisation and schema ---------------------------------------------

class SerialisationAndSchema(unittest.TestCase):

    def setUp(self):
        self.result, self.internal, self.external, _e = build_pair()
        S.compare_values(self.result, self.internal, self.external, subject="revenue")
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            self.schema = json.load(handle)

    def test_38_serialisation_is_byte_identical_on_repeat(self):
        first = self.result.to_json(indent=2)
        second = self.result.to_json(indent=2)
        self.assertEqual(first, second)
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_39_schema_validates(self):
        record = json.loads(self.result.to_json())
        self.assertEqual(jsonschema_mini.validate(record, self.schema), [])
        self.assertEqual(record["recommendations"], [])

    def test_40_every_dimension_and_the_canonical_value_survive(self):
        record = json.loads(self.result.to_json())
        by_id = dict((i["synthesis_id"], i) for i in record["items"])
        for item, expected_kind in ((self.internal, sc.CALCULATION),
                                    (self.external, sc.SOURCED)):
            serialised = by_id[item.id]
            self.assertEqual(serialised["kind"], expected_kind)
            self.assertEqual(serialised["unit"], kpi_contract.CURRENCY)
            self.assertEqual(serialised["currency"], CURRENCY)
            self.assertEqual(serialised["observed"], "12500000")
            for dimension in S.DIMENSIONS:
                self.assertIsNotNone(serialised.get(dimension), dimension)
            self.assertTrue(serialised["provenance"])
            self.assertTrue(serialised["confidence"])

    def test_41_materiality_and_trust_survive(self):
        record = json.loads(self.result.to_json())
        by_id = dict((i["synthesis_id"], i) for i in record["items"])
        self.assertEqual(by_id[self.internal.id]["materiality"]["outcome"],
                         materiality_mod.MATERIAL)
        self.assertEqual(by_id[self.external.id]["trust"], S.UNTRUSTED)
        self.assertEqual(record["trust"], S.UNTRUSTED)


# -- 8. security -------------------------------------------------------------

class SecurityControlsRemainActive(unittest.TestCase):

    def setUp(self):
        self.result, self.internal, self.external, self.evidence = build_pair()

    def test_42_cannot_forge_an_arbitrary_quantity_type(self):
        for bogus in ("GBP million", "GBP bn", "turnover"):
            with self.assertRaises(S.SynthesisError):
                S.sourced_statement(self.result, S.ORIGIN_COMPANY, "x",
                                    evidence_ids=[self.evidence.id], unit=bogus)

    def test_43_cannot_forge_an_internal_origin(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(sc.SynthesisItem(
                sc.CALCULATION, S.ORIGIN_FINANCIAL, "Revenue is GBP 12,500,000.",
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id)],
                unit=kpi_contract.CURRENCY, currency=CURRENCY, basis="from the source"))

    def test_44_cannot_forge_verified_true(self):
        with self.assertRaises(S.SynthesisError):
            self.result.register_claims([
                {"statement": SOURCE_TEXT, "evidence_id": self.evidence.id,
                 "verified": True}])

    def test_45_cannot_forge_a_source_tier(self):
        forged = synthetic_evidence(tier="A")
        fresh = S.SynthesisSet(subject="tier forgery probe")
        with self.assertRaises(S.SynthesisError):
            S.register_external(fresh, _set_of(forged), S.ORIGIN_COMPANY)

    def test_46_cannot_bypass_provenance(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(sc.SynthesisItem(
                sc.SOURCED, S.ORIGIN_COMPANY, "x",
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-does-not-exist")]))

    def test_47_a_serialised_evidence_set_is_refused(self):
        fresh = S.SynthesisSet(subject="dict probe")
        with self.assertRaises(S.SynthesisError):
            S.register_external(fresh, _set_of(synthetic_evidence()).as_dict(),
                                S.ORIGIN_COMPANY)

    def test_48_scale_notation_cannot_reach_another_dimension(self):
        self.assertEqual(self.external.metric_definition, DEFINITION)
        self.assertEqual(self.external.scope, SCOPE)
        self.assertEqual(self.external.period, PERIOD)
        self.assertEqual(self.external.geography, GEOGRAPHY)
        self.assertEqual(self.external.methodology, METHODOLOGY)

    def test_49_notation_and_caller_currency_may_not_disagree(self):
        with self.assertRaises(S.SynthesisError):
            S.sourced_statement(self.result, S.ORIGIN_COMPANY, "x",
                                evidence_ids=[self.evidence.id],
                                observed=SOURCE_VALUE, currency="USD",
                                source_unit="GBP million")

    def test_50_the_allow_result_was_not_manually_set(self):
        """The record comes from the engine: it carries the engine's own fields."""
        comparison = S.compare(self.internal, self.external)
        self.assertEqual(sorted(comparison.keys()),
                         sorted(["status", "checked", "matched", "mismatched",
                                 "unknown", "reason", "converted"]))
        self.assertEqual(comparison["checked"], list(S.DIMENSIONS))
        self.assertEqual(comparison["reason"], S.compatibility.REASON[S.COMPATIBLE])


if __name__ == "__main__":
    unittest.main()
