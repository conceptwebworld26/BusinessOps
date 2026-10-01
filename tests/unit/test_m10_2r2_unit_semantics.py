"""M10.2-R.2 — canonical unit semantics (ADR-0025).

A unit names a **quantity type** and nothing else. The magnitude lives in the `Decimal`
value in base units, the currency code lives in its own field, and display formatting lives
in `render`. `"USD billion"` is therefore not a unit: it is three facts, two of which are
already carried elsewhere.

The failure this closes is specific and quiet. `compatibility.compare()` tests the unit
dimension by exact string equality, so two statements both labelled `"USD billion"` match on
the token while one holds `3400000000` and the other `282.8` — a comparison certified
correct and wrong by a factor of a billion. Strict equality is only safe once the token
carries no magnitude, which makes this an argument *from* strictness rather than against it.

Canonicalisation therefore happens at **statement construction** and nowhere else.
`compare()` is unchanged by this milestone and converts nothing; these tests assert that
directly rather than trusting it.

Everything here is offline and deterministic: reserved `.invalid` hosts, no network, no
scout, no retrieval.
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
from bops import quantity as Q                              # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.kpi import contract as kpi_contract               # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402

from fixtures.build_synthesis_fixtures import (            # noqa: E402
    demo_evidence, evidence_set_with, new_set,
)

SCHEMA_PATH = os.path.join(REPO_ROOT, "lib", "schemas", "synthesis.schema.json")

#: Seven dimensions, stated and agreeing, in canonical form.
AGREED = {
    "metric_definition": "net revenue, after trade discount, before VAT",
    "period": "FY2025 (calendar)",
    "geography": "demo territory",
    "currency": "USD",
    "unit": kpi_contract.CURRENCY,
    "scope": "total revenue of DEMO Widgets Ltd",
    "methodology": "sum of transaction net revenue within the reporting period",
}


def _external(result, evidence, **overrides):
    """One external SOURCED statement carrying the agreed dimensions unless overridden."""
    fields = dict(AGREED)
    observed = overrides.pop("observed", Decimal("3400000000"))
    statement = overrides.pop("statement", "DEMO House reports revenue.")
    fields.update(overrides)
    return S.sourced_statement(
        result, S.ORIGIN_INDUSTRY, statement, evidence_ids=[evidence.id],
        metric="revenue", observed=observed, **fields)


def _set_with_evidence():
    result = new_set(currency="USD")
    evidence = demo_evidence()
    S.register_external(result, evidence_set_with(evidence), S.ORIGIN_INDUSTRY)
    return result, evidence


# -- A. quantity vocabulary --------------------------------------------------

class QuantityVocabulary(unittest.TestCase):
    """One closed list, with no caller-controlled entries."""

    def test_1_every_canonical_quantity_type_is_accepted(self):
        result, evidence = _set_with_evidence()
        for quantity_type in kpi_contract.QUANTITY_TYPES:
            item = sc.SynthesisItem(
                sc.SOURCED, S.ORIGIN_INDUSTRY, "x %s" % quantity_type,
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, evidence.id)],
                unit=quantity_type)
            self.assertEqual(item.unit, quantity_type)

    def test_2_arbitrary_quantity_type_is_refused(self):
        for bogus in ("USD billion", "USD bn", "$m", "units sold", "widgets"):
            with self.assertRaises(S.SynthesisError):
                sc.SynthesisItem(sc.SOURCED, S.ORIGIN_INDUSTRY, "x",
                                 provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-1")],
                                 unit=bogus)

    def test_3_empty_quantity_type_is_refused(self):
        for empty in ("", "   "):
            with self.assertRaises(S.SynthesisError):
                sc.SynthesisItem(sc.SOURCED, S.ORIGIN_INDUSTRY, "x",
                                 provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-1")],
                                 unit=empty)

    def test_3b_none_means_not_stated_and_is_legitimate(self):
        item = sc.SynthesisItem(sc.SOURCED, S.ORIGIN_INDUSTRY, "x",
                                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-1")],
                                unit=None)
        self.assertIsNone(item.unit)

    def test_4_vocabulary_membership_is_exact_not_normalised(self):
        """The repository convention is exact tokens; `compare()` does the case-folding.

        Accepting `"Currency"` here would create a second spelling of one concept and put
        the vocabulary check and the comparison check on different rules.
        """
        for variant in ("Currency", "CURRENCY", " currency"):
            with self.assertRaises(S.SynthesisError):
                sc.SynthesisItem(sc.SOURCED, S.ORIGIN_INDUSTRY, "x",
                                 provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-1")],
                                 unit=variant)

    def test_5_percent_is_distinct_from_percentage_points(self):
        """20% is a rate; 20 percentage points is a change in a rate. Not the same type."""
        self.assertNotEqual(kpi_contract.PERCENT, kpi_contract.PERCENTAGE_POINTS)
        self.assertIn(kpi_contract.PERCENT, kpi_contract.QUANTITY_TYPES)
        self.assertIn(kpi_contract.PERCENTAGE_POINTS, kpi_contract.QUANTITY_TYPES)

    def test_5b_there_is_exactly_one_vocabulary(self):
        self.assertEqual(
            kpi_contract.QUANTITY_TYPES,
            ("currency", "percent", "ratio", "count", "days", "percentage_points"))
        self.assertEqual(kpi_contract.MONETARY_QUANTITY_TYPES, ("currency",))

    def test_5c_the_kpi_engine_reads_the_same_monetary_list(self):
        from bops.kpi import engine as kpi_engine
        self.assertIs(kpi_engine.MONETARY_UNITS, kpi_contract.MONETARY_QUANTITY_TYPES)


# -- B. monetary normalisation -----------------------------------------------

class MonetaryNormalisation(unittest.TestCase):
    """Scale is applied to the value, exactly, in Decimal."""

    def _amount(self, value, unit_text):
        amount, quantity_type, currency = Q.canonical_amount(value, unit_text=unit_text)
        self.assertEqual(quantity_type, kpi_contract.CURRENCY)
        return amount, currency

    def test_6_usd_3_point_4_billion(self):
        amount, currency = self._amount(Decimal("3.4"), "USD billion")
        self.assertEqual(amount, Decimal("3400000000"))
        self.assertEqual(str(amount), "3400000000")
        self.assertEqual(currency, "USD")

    def test_7_usd_3400_million_is_the_same_quantity(self):
        amount, _ = self._amount(Decimal("3400"), "USD million")
        self.assertEqual(amount, Decimal("3400000000"))

    def test_8_usd_already_in_base_units_is_unchanged(self):
        amount, _ = self._amount(Decimal("3400000000"), "USD")
        self.assertEqual(amount, Decimal("3400000000"))

    def test_8b_all_three_notations_agree_exactly(self):
        first, _ = self._amount(Decimal("3.4"), "USD billion")
        second, _ = self._amount(Decimal("3400"), "USD million")
        third, _ = self._amount(Decimal("3400000000"), "USD")
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(str(first), str(second), "serialisation must agree, not just value")
        self.assertEqual(str(second), str(third))

    def test_9_usd_3_point_4_million(self):
        amount, _ = self._amount(Decimal("3.4"), "USD million")
        self.assertEqual(amount, Decimal("3400000"))

    def test_10_usd_3_point_4_thousand(self):
        amount, _ = self._amount(Decimal("3.4"), "USD thousand")
        self.assertEqual(amount, Decimal("3400"))

    def test_11_usd_3_point_4_trillion(self):
        amount, _ = self._amount(Decimal("3.4"), "USD trillion")
        self.assertEqual(amount, Decimal("3400000000000"))

    def test_12_no_floating_point_drift(self):
        """0.1 + 0.2 is the classic float failure; the same shape must be exact here."""
        amount, _ = self._amount(Decimal("0.1"), "USD billion")
        self.assertEqual(amount, Decimal("100000000"))
        third, _ = self._amount(Decimal("1") / Decimal("3"), "USD thousand")
        self.assertEqual(third, Decimal("333.3333333333333333333333333"))
        with self.assertRaises(Q.QuantityError):
            Q.canonical_amount(3.4, unit_text="USD billion")

    def test_13_negative_values_preserve_sign(self):
        amount, _ = self._amount(Decimal("-3.4"), "USD million")
        self.assertEqual(amount, Decimal("-3400000"))

    def test_14_malformed_magnitude_rejects(self):
        for bad in ("", "  ", "not a number", None, True, [1]):
            with self.assertRaises(Q.QuantityError):
                Q.canonical_amount(bad, unit_text="USD million")

    def test_15_unsupported_scale_rejects(self):
        for bad in ("USD gazillion", "USD squillion", "USD lakh", "USD crore"):
            with self.assertRaises(Q.QuantityError):
                Q.canonical_amount(Decimal("1"), unit_text=bad)

    def test_15b_ambiguous_scale_aliases_are_absent_on_purpose(self):
        """`b` and `mm` are not aliases: they mean different things in different markets."""
        for ambiguous in ("USD b", "USD mm"):
            with self.assertRaises(Q.QuantityError):
                Q.canonical_amount(Decimal("1"), unit_text=ambiguous)

    def test_15c_two_scale_words_in_one_notation_reject(self):
        with self.assertRaises(Q.QuantityError):
            Q.canonical_amount(Decimal("1"), unit_text="USD million billion")

    def test_16_a_bare_dollar_sign_establishes_no_currency(self):
        """Four currencies use `$`. An unestablished currency stays unstated."""
        amount, quantity_type, currency = Q.canonical_amount(
            Decimal("226.36"), unit_text="billion")
        self.assertEqual(amount, Decimal("226360000000"))
        self.assertEqual(quantity_type, kpi_contract.CURRENCY)
        self.assertIsNone(currency)

    def test_16b_missing_currency_rejects_monetary_compatibility(self):
        result, evidence = _set_with_evidence()
        stated = _external(result, evidence)
        unstated = _external(result, evidence, currency=None,
                             statement="A source states a figure without naming a currency.")
        comparison = S.compare(stated, unstated)
        self.assertEqual(comparison["status"], S.UNKNOWN)
        self.assertIn("currency", [u["dimension"] for u in comparison["unknown"]])
        self.assertFalse(S.may_combine(comparison))

    def test_16c_an_invented_currency_code_rejects(self):
        for bad in ("usd", "US", "USDD", "$"):
            with self.assertRaises(Q.QuantityError):
                Q.canonical_amount(Decimal("1"), scale="million", currency=bad)

    def test_16d_notation_and_caller_currency_may_not_disagree(self):
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError):
            S.sourced_statement(result, S.ORIGIN_INDUSTRY, "x",
                                evidence_ids=[evidence.id], observed=Decimal("1"),
                                currency="GBP", source_unit="USD billion")


# -- C. compatibility --------------------------------------------------------

class CompatibilityUnderCanonicalUnits(unittest.TestCase):

    def setUp(self):
        self.result, self.evidence = _set_with_evidence()

    def test_17_legacy_usd_billion_input_becomes_canonical_and_can_match(self):
        """The construction seam is what makes the two sides comparable, not `compare()`."""
        canonical = _external(self.result, self.evidence, observed=Decimal("3400000000"))
        from_notation = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY, "A source publishes USD 3.4 billion.",
            evidence_ids=[self.evidence.id], metric="revenue",
            observed=Decimal("3.4"), source_unit="USD billion",
            **{k: v for k, v in AGREED.items() if k not in ("unit", "currency")})
        self.assertEqual(from_notation.unit, kpi_contract.CURRENCY)
        self.assertEqual(from_notation.currency, "USD")
        self.assertEqual(from_notation.observed, Decimal("3400000000"))
        comparison = S.compare(canonical, from_notation)
        self.assertEqual(comparison["status"], S.COMPATIBLE)

    def test_18_usd_million_and_usd_billion_canonicalise_to_one_quantity_type(self):
        shared = {k: v for k, v in AGREED.items() if k not in ("unit", "currency")}
        in_millions = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY, "Source A: USD 3,400 million.",
            evidence_ids=[self.evidence.id], metric="revenue",
            observed=Decimal("3400"), source_unit="USD million", **shared)
        in_billions = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY, "Source B: USD 3.4 billion.",
            evidence_ids=[self.evidence.id], metric="revenue",
            observed=Decimal("3.4"), source_unit="USD billion", **shared)
        self.assertEqual(in_millions.unit, in_billions.unit)
        self.assertEqual(in_millions.observed, in_billions.observed)
        self.assertEqual(S.compare(in_millions, in_billions)["status"], S.COMPATIBLE)

    def test_19_gbp_and_usd_remain_incompatible(self):
        usd = _external(self.result, self.evidence)
        gbp = _external(self.result, self.evidence, currency="GBP",
                        statement="A source reports the same figure in GBP.")
        comparison = S.compare(usd, gbp)
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        self.assertIn("currency", [m["dimension"] for m in comparison["mismatched"]])

    def test_20_currency_and_percent_are_incompatible(self):
        money = _external(self.result, self.evidence)
        rate = _external(self.result, self.evidence, unit=kpi_contract.PERCENT,
                         statement="A source reports a rate.")
        comparison = S.compare(money, rate)
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        self.assertIn("unit", [m["dimension"] for m in comparison["mismatched"]])

    def test_21_currency_and_percentage_points_are_incompatible(self):
        money = _external(self.result, self.evidence)
        points = _external(self.result, self.evidence,
                           unit=kpi_contract.PERCENTAGE_POINTS,
                           statement="A source reports a change in a rate.")
        self.assertEqual(S.compare(money, points)["status"], S.INCOMPATIBLE)

    def test_21b_percent_and_percentage_points_are_incompatible(self):
        rate = _external(self.result, self.evidence, unit=kpi_contract.PERCENT,
                         statement="A rate.")
        points = _external(self.result, self.evidence,
                           unit=kpi_contract.PERCENTAGE_POINTS,
                           statement="A change in a rate.")
        self.assertEqual(S.compare(rate, points)["status"], S.INCOMPATIBLE)

    def test_22_an_unstated_unit_never_becomes_compatible(self):
        stated = _external(self.result, self.evidence)
        unstated = _external(self.result, self.evidence, unit=None,
                             statement="A source states no unit.")
        comparison = S.compare(stated, unstated)
        self.assertEqual(comparison["status"], S.UNKNOWN)
        self.assertFalse(S.may_combine(comparison))

    def test_23_all_seven_canonical_dimensions_matching_allows(self):
        left = _external(self.result, self.evidence, statement="Source A.")
        right = _external(self.result, self.evidence, statement="Source B.")
        comparison = S.compare(left, right)
        self.assertEqual(comparison["status"], S.COMPATIBLE)
        self.assertEqual(sorted(comparison["matched"]), sorted(S.DIMENSIONS))
        self.assertEqual(comparison["mismatched"], [])
        self.assertEqual(comparison["unknown"], [])
        self.assertTrue(S.may_combine(comparison))

    def _reject_on(self, dimension, other_value):
        left = _external(self.result, self.evidence, statement="Source A.")
        right = _external(self.result, self.evidence, statement="Source B.",
                          **{dimension: other_value})
        comparison = S.compare(left, right)
        self.assertNotEqual(comparison["status"], S.COMPATIBLE)
        self.assertFalse(S.may_combine(comparison))
        return comparison

    def test_24_metric_definition_mismatch_rejects(self):
        self._reject_on("metric_definition", "total industry output")

    def test_25_period_mismatch_rejects(self):
        self._reject_on("period", "FY2026 (calendar)")

    def test_26_geography_mismatch_rejects(self):
        self._reject_on("geography", "global")

    def test_27_scope_mismatch_rejects(self):
        self._reject_on("scope", "the whole demo widget industry")

    def test_28_methodology_mismatch_rejects(self):
        self._reject_on("methodology", "top-down vendor estimate")

    def test_28b_revenue_and_market_size_cannot_match(self):
        """Canonical units do not make a firm's revenue comparable to a market's size."""
        revenue = _external(self.result, self.evidence, statement="Our revenue.")
        market = _external(self.result, self.evidence, statement="The market.",
                           metric_definition="total industry output",
                           scope="the whole demo widget industry")
        comparison = S.compare(revenue, market)
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        mismatched = [m["dimension"] for m in comparison["mismatched"]]
        self.assertIn("metric_definition", mismatched)
        self.assertIn("scope", mismatched)


# -- D. no conversion --------------------------------------------------------

class NothingConverts(unittest.TestCase):

    def setUp(self):
        self.result, self.evidence = _set_with_evidence()

    def test_29_and_30_no_currency_conversion_exists(self):
        self.assertFalse(hasattr(Q, "convert_currency"))
        self.assertFalse(hasattr(Q, "exchange_rate"))
        source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "quantity.py"),
                      encoding="utf-8").read().lower()
        for forbidden in ("exchange_rate", "fx_rate", "rate_table", "convert_currency"):
            self.assertNotIn(forbidden + " =", source)
        with self.assertRaises(Q.QuantityError):
            Q.canonical_amount(Decimal("1"), scale="million", currency="GBP→USD")

    def test_31_compare_performs_no_normalisation(self):
        """Two statements differing only in scale label are *not* reconciled by compare().

        `compare()` sees canonical inputs because construction made them canonical. Given
        non-canonical inputs it would not rescue them, and this asserts that directly.
        """
        self.assertTrue(S.NEVER_CONVERTS)
        left = {"metric_definition": "d", "period": "p", "geography": "g",
                "currency": "USD", "unit": "currency", "scope": "s",
                "methodology": "m"}
        right = dict(left, unit="percent")
        comparison = S.compare(left, right)
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        self.assertFalse(comparison["converted"])

    def test_32_normalisation_happens_before_compare(self):
        item = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY, "USD 3.4 billion.",
            evidence_ids=[self.evidence.id], metric="revenue",
            observed=Decimal("3.4"), source_unit="USD billion",
            **{k: v for k, v in AGREED.items() if k not in ("unit", "currency")})
        # Canonical the moment it exists, with no comparison having happened.
        self.assertEqual(item.observed, Decimal("3400000000"))
        self.assertEqual(item.unit, kpi_contract.CURRENCY)

    def test_33_converted_flag_is_false_on_every_outcome(self):
        left = _external(self.result, self.evidence, statement="A.")
        for overrides in ({}, {"currency": "GBP"}, {"unit": None},
                          {"metric_definition": "other"}):
            right = _external(self.result, self.evidence, statement="B.", **overrides)
            self.assertFalse(S.compare(left, right)["converted"])

    def test_34_no_hidden_rate_lookup_in_the_compatibility_module(self):
        source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                                   "compatibility.py"), encoding="utf-8").read()
        for forbidden in ("quantity", "canonical_amount", "scale", "rate", "convert"):
            self.assertNotIn("import %s" % forbidden, source)
        self.assertNotIn("SCALES", source)


# -- E. provenance and security ----------------------------------------------

class UntrustedSourcesCannotForge(unittest.TestCase):

    def setUp(self):
        self.result, self.evidence = _set_with_evidence()

    def test_35_external_evidence_cannot_forge_a_quantity_type(self):
        """Retrieved text naming its own unit cannot put that string in the dimension."""
        with self.assertRaises(S.SynthesisError):
            S.sourced_statement(self.result, S.ORIGIN_INDUSTRY, "x",
                                evidence_ids=[self.evidence.id], unit="USD billion")

    def test_36_external_evidence_cannot_forge_a_currency(self):
        amount, _kind, currency = Q.canonical_amount(Decimal("1"), unit_text="billion")
        self.assertIsNone(currency, "a scale word alone establishes no currency")
        with self.assertRaises(Q.QuantityError):
            Q.canonical_amount(Decimal("1"), scale="billion", currency="Dollars")

    def test_37_external_evidence_cannot_become_an_internal_calculation(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(sc.SynthesisItem(
                sc.CALCULATION, S.ORIGIN_FINANCIAL, "Revenue is USD 3.4bn.",
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id)],
                unit=kpi_contract.CURRENCY, currency="USD", basis="derived"))

    def test_38_verified_true_remains_rejected(self):
        with self.assertRaises(S.SynthesisError):
            self.result.register_claims([
                {"statement": "x", "evidence_id": self.evidence.id, "verified": True}])

    def test_39_forged_source_tier_remains_rejected(self):
        victim = demo_evidence(tier="A", host="research.example.invalid")
        with self.assertRaises(S.SynthesisError):
            S.register_external(new_set(), evidence_set_with(victim), S.ORIGIN_INDUSTRY)

    def test_40_provenance_footing_remains_enforced(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(sc.SynthesisItem(
                sc.FACT, S.ORIGIN_FINANCIAL, "x",
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id)]))

    def test_40b_source_tier_is_still_recomputed_locally(self):
        stored = self.result.resolve_ref(
            sc.ProvenanceRef(sc.P_EVIDENCE, self.evidence.id))
        self.assertEqual(stored.source_tier, "C")
        self.assertEqual(stored.trust, S.UNTRUSTED)

    def test_40c_a_scale_cannot_reach_an_unrelated_field(self):
        before = dict(metric_definition=AGREED["metric_definition"],
                      scope=AGREED["scope"], period=AGREED["period"])
        item = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY, "USD 3.4 billion.",
            evidence_ids=[self.evidence.id], metric="revenue",
            observed=Decimal("3.4"), source_unit="USD billion",
            **{k: v for k, v in AGREED.items() if k not in ("unit", "currency")})
        self.assertEqual(item.metric_definition, before["metric_definition"])
        self.assertEqual(item.scope, before["scope"])
        self.assertEqual(item.period, before["period"])
        self.assertEqual(item.kind, sc.SOURCED)
        self.assertEqual(item.domain, "external")


# -- F. serialisation and schema ---------------------------------------------

class SerialisationAndSchema(unittest.TestCase):

    def setUp(self):
        self.result, self.evidence = _set_with_evidence()
        # A materiality verdict is carried so its survival can be asserted; the
        # serialiser omits empty fields, so an item without one proves nothing.
        self.item = _external(
            self.result, self.evidence,
            materiality={"outcome": "material", "reason": "above the demo threshold"})
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            self.schema = json.load(handle)

    def test_41_and_42_serialisation_is_deterministic_and_repeatable(self):
        first = self.result.to_json(indent=2)
        second = self.result.to_json(indent=2)
        self.assertEqual(first, second)
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_43_schema_accepts_a_canonical_monetary_statement(self):
        record = json.loads(self.result.to_json())
        self.assertEqual(jsonschema_mini.validate(record, self.schema), [])
        serialised = [i for i in record["items"] if i["synthesis_id"] == self.item.id][0]
        self.assertEqual(serialised["unit"], kpi_contract.CURRENCY)
        self.assertEqual(serialised["currency"], "USD")

    def test_44_schema_rejects_a_magnitude_qualified_unit(self):
        record = json.loads(self.result.to_json())
        for entry in record["items"]:
            if entry["synthesis_id"] == self.item.id:
                entry["unit"] = "USD billion"
        errors = jsonschema_mini.validate(record, self.schema)
        self.assertTrue(errors, "the schema must refuse a magnitude-qualified unit")
        self.assertTrue(any("unit" in str(e) for e in errors))

    def test_44b_schema_accepts_an_unstated_unit(self):
        record = json.loads(self.result.to_json())
        for entry in record["items"]:
            if entry["synthesis_id"] == self.item.id:
                entry["unit"] = None
        self.assertEqual(jsonschema_mini.validate(record, self.schema), [])

    def test_45_46_47_provenance_materiality_confidence_survive(self):
        record = json.loads(self.result.to_json())
        serialised = [i for i in record["items"] if i["synthesis_id"] == self.item.id][0]
        self.assertTrue(serialised["provenance"])
        self.assertEqual(serialised["materiality"]["outcome"], "material")
        self.assertTrue(serialised["confidence"])
        self.assertEqual(record["recommendations"], [])


# -- G. regression -----------------------------------------------------------

class ExistingBehaviourUnchanged(unittest.TestCase):
    """The engine's own output must be semantically what it was before ADR-0025."""

    @classmethod
    def setUpClass(cls):
        from bops import commands
        context = json.load(open(
            os.path.join(REPO_ROOT, "assets", "demo-data", "business_context.json"),
            encoding="utf-8"))
        cls.outcome = commands.run(
            "profitability-analysis",
            os.path.join(REPO_ROOT, "assets", "demo-data", "northwind_sales.csv"),
            context_overrides=context)

    def test_48_kpi_units_remain_canonical_quantity_types(self):
        for result in self.outcome.result.kpis.values():
            self.assertTrue(kpi_contract.is_quantity_type(result.definition.unit),
                            "%s carries %r" % (result.kpi_id, result.definition.unit))

    def test_49_analytics_findings_carry_canonical_quantity_types(self):
        units = set()
        for analysis in self.outcome.analyses.values():
            for finding in analysis.findings:
                if finding.unit is not None:
                    units.add(finding.unit)
                    self.assertTrue(kpi_contract.is_quantity_type(finding.unit),
                                    "finding carries %r" % (finding.unit,))
        self.assertIn(kpi_contract.CURRENCY, units)
        self.assertIn(kpi_contract.PERCENTAGE_POINTS, units)

    def test_49b_revenue_is_unchanged_by_this_milestone(self):
        revenue = [f for f in self.outcome.analyses["financial"].findings
                   if f.metric == "revenue"][0]
        self.assertEqual(revenue.observed, Decimal("3467850.16"))
        self.assertEqual(revenue.unit, kpi_contract.CURRENCY)
        self.assertEqual(revenue.currency, "GBP")

    def test_50_internal_findings_still_enter_synthesis_unchanged(self):
        result = new_set(currency="GBP")
        produced = S.from_analysis_set(
            result, self.outcome.analyses["financial"], S.ORIGIN_FINANCIAL,
            dataset_id="ds-test")
        self.assertTrue(produced)
        revenue = [i for i in produced if i.metric == "revenue"][0]
        self.assertEqual(revenue.kind, sc.CALCULATION)
        self.assertEqual(revenue.unit, kpi_contract.CURRENCY)
        self.assertEqual(revenue.currency, "GBP")
        self.assertEqual(revenue.observed, Decimal("3467850.16"))
        self.assertEqual(revenue.support, S.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
