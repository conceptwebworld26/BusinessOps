# -*- coding: utf-8 -*-
"""M10.2-R.6 — dimension provenance and source-context admissibility (ADR-0026).

M10.2-R.4 returned `unknown` for geography, currency and methodology, and it did so for
the right reason. But the run also exposed that the result depended on the caller's
restraint: nothing in the synthesis layer stopped a caller writing `currency="USD"` from
background knowledge, and nothing in the serialised record would have shown it was a guess.

These tests exercise the control that closes that gap. **Every fixture here is synthetic.**
`acme-filings.example.invalid` and `other-source.example.invalid` are reserved hosts that
can never resolve, `Acme Industrial plc` is not a company, and the figures are invented for
this module. Nothing here reaches a network and nothing here is a real-world observation.
"""

import copy
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
from bops import synthesis as S                             # noqa: E402
from bops.analytics import contract as ac                   # noqa: E402
from bops.kpi import contract as kpi_contract               # noqa: E402
from bops.research import evidence_set as ev_mod            # noqa: E402
from bops.synthesis import compatibility as compat          # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402
from bops.synthesis import dimension_provenance as dp       # noqa: E402

SCHEMA_PATH = os.path.join(REPO_ROOT, "lib", "schemas", "synthesis.schema.json")

# -- the synthetic document --------------------------------------------------

OPERATION = "op-m102r6-fixture"
OTHER_OPERATION = "op-m102r6-other"
DOC = "https://acme-filings.example.invalid/acme-fy2025-annual-report.htm"
OTHER_DOC = "https://other-source.example.invalid/commentary-on-acme.htm"
SOURCE = "SYNTHETIC Acme Industrial plc filings archive (test fixture)"

METRIC_TEXT = ("Total revenue for the year ended 31 December 2025 was USD 4.2 billion.")
CONTEXT_TEXT = ("Amounts are stated in US dollars. The consolidated results represent the "
                "company's worldwide operations and are prepared on an accrual basis.")
WHOLE_DOC = METRIC_TEXT + " " + CONTEXT_TEXT

DEFINITION = "total revenue"
PERIOD = "year ended 31 December 2025"
GEOGRAPHY = "worldwide"
CURRENCY = "USD"
SCOPE = "consolidated"
METHODOLOGY = "accrual basis"

APPLICABILITY = {"period": PERIOD, "scope": SCOPE}


def item(reference=DOC, operation=OPERATION, content=WHOLE_DOC, item_id=None,
         source=SOURCE, title=None):
    return ev_mod.EvidenceItem(
        source=source, reference=reference, source_tier="C", retrieved_at="2026-09-15",
        title=title or "Acme Industrial plc annual report 2025",
        publication_date="2026-03-31", source_type=ev_mod.FILING, content=content,
        claim_kind="financials", operation=operation, as_of="2026-09-15",
        item_id=item_id)


def evidence_set(*items):
    result = ev_mod.EvidenceSet(operation=OPERATION, subject="Acme Industrial plc",
                               category="company", query_text="acme fy2025 revenue",
                               destination={"kind": "public_web"}, disclosure_tier=0)
    for entry in items:
        result.add(entry)
    return result


def footings(evidence_id, **overrides):
    """The seven footings the synthetic document genuinely supports."""
    spec = [
        ("metric_definition", DEFINITION, dp.STATED, "Total revenue"),
        ("period", PERIOD, dp.STATED, "year ended 31 December 2025"),
        ("geography", GEOGRAPHY, dp.CONTEXT, "worldwide operations"),
        ("currency", CURRENCY, dp.STATED, "USD"),
        ("scope", SCOPE, dp.CONTEXT, "consolidated results"),
        ("methodology", METHODOLOGY, dp.CONTEXT, "accrual basis"),
    ]
    built = []
    for dimension, value, basis, excerpt in spec:
        built.append(dp.DimensionProvenance(
            dimension, value, basis, evidence_id=overrides.get(dimension, evidence_id),
            source_excerpt=excerpt, source_locator="body",
            applicability=dict(APPLICABILITY)))
    built.append(dp.DimensionProvenance(
        "unit", kpi_contract.CURRENCY, dp.DERIVED,
        evidence_id=overrides.get("unit", evidence_id),
        derivation="adr0025.canonical_amount.quantity_type"))
    return built


def build(evidence_items=None, provenance=None, strict=False, **dimension_overrides):
    """One synthesis set holding the external statement. Returns `(set, item, evidence)`."""
    items = list(evidence_items or [item()])
    primary = items[0]
    result = S.SynthesisSet(subject="M10.2-R.6 fixture",
                            require_dimension_provenance=strict)
    S.register_external(result, evidence_set(*items), S.ORIGIN_COMPANY)
    dimensions = {"metric_definition": DEFINITION, "period": PERIOD,
                  "geography": GEOGRAPHY, "scope": SCOPE, "methodology": METHODOLOGY}
    dimensions.update(dimension_overrides)
    statement = S.sourced_statement(
        result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
        metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
        dimension_provenance=(footings(primary.id) if provenance is None
                              else provenance),
        **dimensions)
    return result, statement, primary


def internal_twin(result, dataset_id="ds-m102r6"):
    """An internal calculation stating the same seven dimensions, for the ALLOW pair.

    SYNTHETIC VERIFICATION FIXTURE - the value mirrors the synthetic document above so the
    pair is like-for-like. Internal statements are engine-footed (ADR-0023) and carry no
    dimension provenance, which is exactly the asymmetry ADR-0026 describes.
    """
    result.register_dataset(dataset_id, label="synthetic fixture")
    analysis = ac.AnalysisSet("financial", currency=CURRENCY, quality_grade="PASS",
                              provenance={"source_name": "synthetic fixture"})
    analysis.add(ac.AnalysisFinding(
        "financial.kpi.revenue", "financial", ac.CALCULATION,
        "Revenue for the year was USD 4,200,000,000.", metric="revenue", period=PERIOD,
        observed=Decimal("4200000000"), unit=kpi_contract.CURRENCY, currency=CURRENCY,
        basis="sum(net_revenue)", materiality=materiality_mod.MATERIAL,
        materiality_reason="Headline figure."))
    produced = S.from_analysis_set(
        result, analysis, S.ORIGIN_FINANCIAL, dataset_id=dataset_id,
        metric_definition=DEFINITION, geography=GEOGRAPHY, scope=SCOPE,
        methodology=METHODOLOGY)
    return [i for i in produced if i.metric == "revenue"][0]


# ===========================================================================
# Fixtures A-I (section 20)
# ===========================================================================

class FixtureA_Stated(unittest.TestCase):
    """Evidence explicitly establishes a dimension -> admissible."""

    def test_stated_dimension_is_admissible(self):
        _, statement, _ = build()
        self.assertEqual(statement.dimensions["metric_definition"], DEFINITION)
        self.assertEqual(statement.dimensions["currency"], CURRENCY)

    def test_all_seven_resolve_from_the_document(self):
        _, statement, _ = build()
        self.assertEqual(sorted(k for k, v in statement.dimensions.items()
                                if v is not None), sorted(sc.DIMENSIONS))

    def test_resolution_trail_records_every_footing(self):
        _, statement, _ = build()
        self.assertEqual(len(statement.dimension_resolution), 7)
        self.assertTrue(all(r["admitted"] for r in statement.dimension_resolution))

    def test_trail_carries_locally_resolved_source_metadata(self):
        _, statement, evidence = build()
        record = statement.dimension_resolution[0]
        self.assertEqual(record["source_tier"], evidence.source_tier)
        self.assertEqual(record["trust"], "untrusted")
        self.assertEqual(record["reference"], DOC)


class FixtureB_SameDocumentContext(unittest.TestCase):
    """A declaration elsewhere in the same document establishes a dimension."""

    def test_context_dimension_is_admissible(self):
        _, statement, _ = build()
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)
        self.assertEqual(statement.dimensions["methodology"], METHODOLOGY)

    def test_context_may_live_in_a_separate_item_of_the_same_document(self):
        metric = item(content=METRIC_TEXT, item_id="ev-metric")
        context = item(content=CONTEXT_TEXT, item_id="ev-context")
        result = S.SynthesisSet(subject="two items, one document")
        S.register_external(result, evidence_set(metric, context), S.ORIGIN_COMPANY)
        provenance = footings(metric.id, geography=context.id, scope=context.id,
                              methodology=context.id)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[metric.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            metric_definition=DEFINITION, period=PERIOD, geography=GEOGRAPHY,
            scope=SCOPE, methodology=METHODOLOGY, dimension_provenance=provenance)
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)

    def test_statement_text_is_not_rewritten_by_context(self):
        _, statement, _ = build()
        self.assertEqual(statement.statement, METRIC_TEXT)
        self.assertNotIn("US dollars", statement.statement)


class FixtureC_Derived(unittest.TestCase):
    """Quantity semantics derive only from what the source printed (ADR-0025)."""

    def test_derived_unit_is_admissible(self):
        _, statement, _ = build()
        self.assertEqual(statement.dimensions["unit"], kpi_contract.CURRENCY)

    def test_derivation_registry_is_closed(self):
        _, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("unit", "currency", dp.DERIVED,
                                   evidence_id=evidence.id,
                                   derivation="made.up.rule")

    def test_registry_cannot_be_extended_by_a_caller(self):
        self.assertIsInstance(dp.DERIVATION_RULES, frozenset)
        with self.assertRaises(AttributeError):
            dp.DERIVATION_RULES.add("sec.filing.implies.usd")


class FixtureD_Asserted(unittest.TestCase):
    """A dimension without admissible provenance resolves to unknown."""

    def test_asserted_dimension_reads_as_unstated(self):
        _, _, evidence = build()
        provenance = [dp.DimensionProvenance("geography", GEOGRAPHY, dp.ASSERTED)]
        result, statement, _ = build(provenance=provenance)
        self.assertIsNone(statement.dimensions["geography"])

    def test_asserted_dimension_is_still_declared_and_serialised(self):
        provenance = [dp.DimensionProvenance("geography", GEOGRAPHY, dp.ASSERTED)]
        _, statement, _ = build(provenance=provenance)
        self.assertEqual(statement.declared_dimensions["geography"], GEOGRAPHY)
        self.assertEqual(statement.as_dict()["dimension_provenance"][0]["basis"],
                         dp.ASSERTED)

    def test_asserted_basis_is_not_admissible(self):
        self.assertNotIn(dp.ASSERTED, dp.ADMISSIBLE_BASES)
        self.assertIn(dp.ASSERTED, dp.BASES)

    def test_asserted_currency_does_not_reach_compare(self):
        provenance = [dp.DimensionProvenance("currency", CURRENCY, dp.ASSERTED)]
        _, statement, _ = build(provenance=provenance)
        self.assertIsNone(statement.dimensions["currency"])
        record = compat.compare(statement, statement, dimensions=("currency",))
        self.assertEqual(record["status"], compat.UNKNOWN)


class FixtureE_ConflictingContext(unittest.TestCase):
    """Two admissible sources disagreeing leave the dimension unresolved."""

    def setUp(self):
        self.doc = item(content=WHOLE_DOC + " The results are prepared on a cash basis.")
        self.result = S.SynthesisSet(subject="conflicting context")
        S.register_external(self.result, evidence_set(self.doc), S.ORIGIN_COMPANY)
        self.statement = S.sourced_statement(
            self.result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[self.doc.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            methodology=METHODOLOGY,
            dimension_provenance=[
                dp.DimensionProvenance("methodology", METHODOLOGY, dp.CONTEXT,
                                       evidence_id=self.doc.id,
                                       source_excerpt="accrual basis",
                                       applicability={"period": None, "scope": None}),
                dp.DimensionProvenance("methodology", "cash basis", dp.CONTEXT,
                                       evidence_id=self.doc.id,
                                       source_excerpt="cash basis",
                                       applicability={"period": None, "scope": None}),
            ])

    def test_conflicting_context_yields_unknown_not_a_winner(self):
        # Applicability is undeclared here, so both refuse before the conflict arises -
        # which is itself the conservative outcome. The dimension is unresolved either way.
        self.assertIsNone(self.statement.dimensions["methodology"])

    def test_conflict_is_recorded_when_both_footings_are_admissible(self):
        doc = item(content=WHOLE_DOC + " The results are prepared on a cash basis.")
        result = S.SynthesisSet(subject="conflicting context, both admissible")
        S.register_external(result, evidence_set(doc), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[doc.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            period=PERIOD, scope=SCOPE, methodology=METHODOLOGY,
            dimension_provenance=[
                dp.DimensionProvenance("methodology", METHODOLOGY, dp.CONTEXT,
                                       evidence_id=doc.id,
                                       source_excerpt="accrual basis",
                                       applicability=dict(APPLICABILITY)),
                dp.DimensionProvenance("methodology", "cash basis", dp.CONTEXT,
                                       evidence_id=doc.id,
                                       source_excerpt="cash basis",
                                       applicability=dict(APPLICABILITY)),
            ])
        self.assertIsNone(statement.dimensions["methodology"])
        self.assertIn("methodology",
                      dp.conflicting_dimensions(statement.dimension_resolution))
        self.assertTrue(result.conflicts)

    def test_no_winner_is_chosen_by_recency_tier_or_order(self):
        trail = [r for r in self.statement.dimension_resolution
                 if r.get("dimension") == "methodology"]
        self.assertFalse(any(r.get("admitted") and r.get("value") == METHODOLOGY
                             and len(trail) == 1 for r in trail))


class FixtureF_WrongDocument(unittest.TestCase):
    """Context from another document is refused. Cross-source context is prohibited."""

    def test_cross_source_context_is_refused(self):
        primary = item()
        other = item(reference=OTHER_DOC, source="Other commentary (fixture)",
                     content=CONTEXT_TEXT)
        result = S.SynthesisSet(subject="cross source")
        S.register_external(result, evidence_set(primary, other), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", GEOGRAPHY, dp.CONTEXT, evidence_id=other.id,
                source_excerpt="worldwide operations",
                applicability=dict(APPLICABILITY))])
        self.assertIsNone(statement.dimensions["geography"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.WRONG_DOCUMENT)

    def test_same_publisher_different_document_is_still_refused(self):
        primary = item()
        sibling = item(reference=DOC.replace("annual-report", "interim-report"),
                       content=CONTEXT_TEXT)
        result = S.SynthesisSet(subject="same publisher")
        S.register_external(result, evidence_set(primary, sibling), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", GEOGRAPHY, dp.CONTEXT, evidence_id=sibling.id,
                source_excerpt="worldwide operations",
                applicability=dict(APPLICABILITY))])
        self.assertIsNone(statement.dimensions["geography"])


class FixtureG_WrongOperation(unittest.TestCase):
    """Evidence from another retrieval operation cannot foot this statement."""

    def test_foreign_operation_is_refused(self):
        primary = item()
        foreign = item(operation=OTHER_OPERATION, item_id="ev-foreign",
                       content=CONTEXT_TEXT)
        result = S.SynthesisSet(subject="foreign operation")
        S.register_external(result, evidence_set(primary, foreign), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", GEOGRAPHY, dp.CONTEXT, evidence_id=foreign.id,
                source_excerpt="worldwide operations",
                applicability=dict(APPLICABILITY))])
        self.assertIsNone(statement.dimensions["geography"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.WRONG_OPERATION)


class FixtureH_WrongApplicability(unittest.TestCase):
    """Context that does not declare it governs this period and scope establishes nothing."""

    def _with_applicability(self, applicability):
        primary = item()
        result = S.SynthesisSet(subject="applicability")
        S.register_external(result, evidence_set(primary), S.ORIGIN_COMPANY)
        return S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            period=PERIOD, scope=SCOPE, geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", GEOGRAPHY, dp.CONTEXT, evidence_id=primary.id,
                source_excerpt="worldwide operations",
                applicability=applicability)])

    def test_wrong_period_is_refused(self):
        statement = self._with_applicability({"period": "year ended 31 December 2024",
                                              "scope": SCOPE})
        self.assertIsNone(statement.dimensions["geography"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.NOT_APPLICABLE)

    def test_wrong_scope_is_refused(self):
        statement = self._with_applicability({"period": PERIOD, "scope": "segment"})
        self.assertIsNone(statement.dimensions["geography"])

    def test_undeclared_applicability_is_not_read_as_everywhere(self):
        statement = self._with_applicability({})
        self.assertIsNone(statement.dimensions["geography"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.NOT_APPLICABLE)

    def test_matching_applicability_is_admitted(self):
        statement = self._with_applicability(dict(APPLICABILITY))
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)


class FixtureI_RoundTrip(unittest.TestCase):
    """A reloaded statement does not regain admissibility from its own JSON."""

    def test_reload_without_registry_yields_unknown(self):
        _, statement, _ = build()
        record = json.loads(json.dumps(statement.as_dict(), default=str))
        rebuilt = sc.SynthesisItem.from_dict(record)
        empty = S.SynthesisSet(subject="no registry")
        with self.assertRaises(sc.SynthesisError):
            empty.add(rebuilt)

    def test_reloaded_item_does_not_carry_a_resolved_view(self):
        _, statement, _ = build()
        record = json.loads(json.dumps(statement.as_dict(), default=str))
        rebuilt = sc.SynthesisItem.from_dict(record)
        self.assertIsNone(rebuilt._resolved_dimensions)
        self.assertEqual(rebuilt.dimension_resolution, [])

    def test_serialised_source_metadata_is_not_restored(self):
        _, statement, _ = build()
        record = json.loads(json.dumps(statement.as_dict(), default=str))
        record["dimension_provenance"][0]["source_tier"] = "A"
        record["dimension_provenance"][0]["trust"] = "trusted"
        rebuilt = sc.SynthesisItem.from_dict(record)
        entry = rebuilt.dimension_provenance[0]
        self.assertFalse(hasattr(entry, "source_tier"))
        self.assertNotIn("source_tier", entry.as_dict())

    def test_footings_survive_reload_and_re_resolve_against_a_live_registry(self):
        _, statement, evidence = build()
        record = json.loads(json.dumps(statement.as_dict(), default=str))
        rebuilt = sc.SynthesisItem.from_dict(record)
        fresh = S.SynthesisSet(subject="rehydrated")
        S.register_external(fresh, evidence_set(item()), S.ORIGIN_COMPANY)
        fresh.add(rebuilt)
        self.assertEqual(rebuilt.dimensions["geography"], GEOGRAPHY)


# ===========================================================================
# Security attack matrix (section 19)
# ===========================================================================

class AttackMatrix(unittest.TestCase):

    def _unbacked(self, dimension, value, excerpt, notation="USD billion"):
        primary = item()
        result = S.SynthesisSet(subject="unbacked")
        S.register_external(result, evidence_set(primary), S.ORIGIN_COMPANY)
        return S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit=notation,
            period=PERIOD, scope=SCOPE, **{dimension: value,
                                           "dimension_provenance": [
                                               dp.DimensionProvenance(
                                                   dimension, value, dp.STATED,
                                                   evidence_id=primary.id,
                                                   source_excerpt=excerpt,
                                                   applicability=dict(APPLICABILITY))]})

    # 1-3: unsupported assertions
    def test_01_currency_usd_without_source_support(self):
        # The notation carries no ISO code, so canonicalisation leaves the currency
        # unstated (ADR-0025). A footing quoting text the source never printed cannot
        # supply one either.
        statement = self._unbacked("currency", "EUR", "stated in euro",
                                   notation="billion")
        self.assertIsNone(statement.dimensions["currency"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.EXCERPT_ABSENT)

    def test_02_geography_global_without_source_support(self):
        statement = self._unbacked("geography", "global",
                                   "operates globally across every continent")
        self.assertIsNone(statement.dimensions["geography"])

    def test_03_methodology_gaap_without_source_support(self):
        statement = self._unbacked("methodology", "US GAAP",
                                   "prepared in accordance with US GAAP")
        self.assertIsNone(statement.dimensions["methodology"])
        self.assertEqual(statement.dimension_resolution[0]["reason"], dp.EXCERPT_ABSENT)

    # 4: injection
    def test_04_hostile_content_cannot_inject_dimension_metadata(self):
        from bops.research import scout as scout_mod
        for field in ("dimension_provenance", "geography", "currency", "methodology",
                      "source_tier", "verified"):
            self.assertNotIn(field, scout_mod.ACCEPTED_RECORD_FIELDS)

    # 5,17: cross-source
    def test_05_context_from_another_source_refused(self):
        FixtureF_WrongDocument("test_cross_source_context_is_refused").debug()

    def test_17_cross_source_context_prohibited_by_design(self):
        self.assertIn("document_mismatch", dp.REASON_TEXT)

    # 6: operation
    def test_06_context_from_another_operation_refused(self):
        FixtureG_WrongOperation("test_foreign_operation_is_refused").debug()

    # 7,8: applicability
    def test_07_wrong_period_refused(self):
        FixtureH_WrongApplicability("test_wrong_period_is_refused").debug()

    def test_08_wrong_scope_refused(self):
        FixtureH_WrongApplicability("test_wrong_scope_is_refused").debug()

    # 9: another document
    def test_09_context_from_another_document_refused(self):
        FixtureF_WrongDocument(
            "test_same_publisher_different_document_is_still_refused").debug()

    # 10: mutation
    def test_10_provenance_is_immutable(self):
        _, _, evidence = build()
        entry = dp.DimensionProvenance("currency", CURRENCY, dp.STATED,
                                       evidence_id=evidence.id, source_excerpt="USD",
                                       applicability=dict(APPLICABILITY))
        for field, value in (("dimension", "geography"), ("value", "EUR"),
                             ("basis", dp.ASSERTED), ("evidence_id", "ev-other"),
                             ("applicability", {}), ("derivation", "x"),
                             ("source_excerpt", "anything")):
            with self.assertRaises(sc.SynthesisError):
                setattr(entry, field, value)
        with self.assertRaises(sc.SynthesisError):
            del entry.value

    # 11,12: derived fields
    def test_11_caller_cannot_supply_source_tier(self):
        _, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("currency", CURRENCY, dp.STATED,
                                   evidence_id=evidence.id, source_excerpt="USD",
                                   source_tier="A")

    def test_12_caller_cannot_supply_verified_or_freshness(self):
        _, _, evidence = build()
        for field in ("verified", "freshness", "trust", "source", "reference",
                      "retrieved_at"):
            with self.assertRaises(sc.SynthesisError):
                dp.DimensionProvenance("currency", CURRENCY, dp.STATED,
                                       evidence_id=evidence.id, source_excerpt="USD",
                                       **{field: "forged"})

    # 13: internal footing
    def test_13_external_context_cannot_foot_an_internal_calculation(self):
        result, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            result.add(sc.SynthesisItem(
                sc.CALCULATION, S.ORIGIN_FINANCIAL, "Our revenue was 4,200,000,000.",
                provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, evidence.id)],
                basis="sum", observed=Decimal("4200000000"),
                unit=kpi_contract.CURRENCY,
                dimension_provenance=footings(evidence.id)))

    # 14: unresolvable on load
    def test_14_unregistered_evidence_yields_unknown(self):
        primary = item()
        result = S.SynthesisSet(subject="unregistered")
        S.register_external(result, evidence_set(primary), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", GEOGRAPHY, dp.CONTEXT, evidence_id="ev-does-not-exist",
                source_excerpt="worldwide operations",
                applicability=dict(APPLICABILITY))])
        self.assertIsNone(statement.dimensions["geography"])
        self.assertEqual(statement.dimension_resolution[0]["reason"],
                         dp.UNRESOLVED_EVIDENCE)

    # 15: conflict
    def test_15_conflicting_context_yields_unknown(self):
        FixtureE_ConflictingContext(
            "test_conflict_is_recorded_when_both_footings_are_admissible").debug()

    # 16: staleness outside applicability
    def test_16_stale_context_outside_applicability_refused(self):
        FixtureH_WrongApplicability("test_wrong_period_is_refused").debug()

    # 18,19: prohibited derivations
    def test_18_source_type_cannot_derive_methodology(self):
        _, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("methodology", "US GAAP", dp.DERIVED,
                                   evidence_id=evidence.id,
                                   derivation="adr0025.canonical_amount.currency_code")
        self.assertNotIn("methodology", dp.DERIVABLE_DIMENSIONS)

    def test_19_company_identity_cannot_derive_geography(self):
        _, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("geography", "global", dp.DERIVED,
                                   evidence_id=evidence.id,
                                   derivation="adr0025.canonical_amount.quantity_type")
        self.assertNotIn("geography", dp.DERIVABLE_DIMENSIONS)

    # 20: bare dollar
    def test_20_bare_dollar_does_not_establish_usd(self):
        from bops import quantity as Q
        amount, quantity_type, currency = Q.canonical_amount(
            Decimal("4.2"), unit_text="billion")
        self.assertEqual(amount, Decimal("4200000000"))
        self.assertEqual(quantity_type, kpi_contract.CURRENCY)
        self.assertIsNone(currency)

    # 21,22: derivation registry
    def test_21_arbitrary_derivation_rule_refused(self):
        _, _, evidence = build()
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("currency", CURRENCY, dp.DERIVED,
                                   evidence_id=evidence.id,
                                   derivation="sec.filing.implies.usd")

    def test_22_derivation_registry_is_immutable(self):
        before = set(dp.DERIVATION_RULES)
        with self.assertRaises(AttributeError):
            dp.DERIVATION_RULES.add("anything")
        self.assertEqual(set(dp.DERIVATION_RULES), before)

    # 23,24,25
    def test_23_asserted_never_reaches_compatibility(self):
        provenance = [dp.DimensionProvenance("currency", CURRENCY, dp.ASSERTED)]
        _, statement, _ = build(provenance=provenance)
        self.assertIsNone(statement.dimensions["currency"])
        self.assertNotIn(dp.ASSERTED, dp.ADMISSIBLE_BASES)

    def test_24_context_admitted_only_when_every_binding_passes(self):
        _, statement, _ = build()
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)

    def test_25_unknown_dimension_stays_unknown(self):
        result, external, _ = build(provenance=[], strict=True)
        internal = internal_twin(result)
        record = compat.compare(internal, external)
        self.assertEqual(record["status"], compat.UNKNOWN)
        self.assertEqual(record["mismatched"], [])

    # 26,27
    def test_26_currency_conversion_unavailable(self):
        source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                                   "dimension_provenance.py"), encoding="utf-8").read()
        for token in ("exchange_rate", "fx_rate", "convert_currency", "RATE_TABLE"):
            self.assertNotIn(token, source)

    def test_27_no_synonym_table_exists(self):
        source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                                   "dimension_provenance.py"), encoding="utf-8").read()
        for token in ("SYNONYM", "synonyms", "ALIASES", "EQUIVALENT"):
            self.assertNotIn(token, source)
        # "global" and "worldwide" are two truthful words for one idea and must NOT match.
        self.assertEqual(compat.compare({"geography": "global"},
                                        {"geography": "worldwide"},
                                        dimensions=("geography",))["status"],
                         compat.INCOMPATIBLE)


# ===========================================================================
# Boundaries that must not move
# ===========================================================================

class CompatibilityBoundary(unittest.TestCase):

    def setUp(self):
        self.source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "synthesis",
                                        "compatibility.py"), encoding="utf-8").read()

    def test_compare_has_no_provenance_logic(self):
        for token in ("provenance", "DimensionProvenance", "evidence", "EvidenceSet",
                      "source_tier", "registry", "admissible", "basis"):
            self.assertNotIn(token, self.source,
                             "compatibility.py must not learn about %s" % token)

    def test_compare_still_converts_nothing(self):
        self.assertTrue(compat.NEVER_CONVERTS)
        for left, right in (({"currency": "USD"}, {"currency": "USD"}),
                            ({"currency": "USD"}, {"currency": "EUR"}),
                            ({"currency": None}, {"currency": "USD"})):
            self.assertFalse(compat.compare(left, right,
                                            dimensions=("currency",))["converted"])

    def test_compare_accepts_a_plain_mapping_unchanged(self):
        record = compat.compare({"geography": "worldwide"}, {"geography": "worldwide"},
                                dimensions=("geography",))
        self.assertEqual(record["status"], compat.COMPATIBLE)

    def test_seven_dimensions_unchanged(self):
        self.assertEqual(sc.DIMENSIONS,
                         ("metric_definition", "period", "geography", "currency",
                          "unit", "scope", "methodology"))

    def test_unknown_never_becomes_compatible(self):
        record = compat.compare({"geography": None}, {"geography": "worldwide"},
                                dimensions=("geography",))
        self.assertEqual(record["status"], compat.UNKNOWN)


class Adr0025Boundary(unittest.TestCase):

    def test_quantity_vocabulary_unchanged(self):
        self.assertEqual(kpi_contract.QUANTITY_TYPES,
                         ("currency", "percent", "ratio", "count", "days",
                          "percentage_points"))

    def test_scale_normalisation_unchanged(self):
        from bops import quantity as Q
        self.assertEqual(Q.canonical_amount(Decimal("4.2"), unit_text="USD billion"),
                         (Decimal("4200000000"), "currency", "USD"))
        self.assertEqual(Q.canonical_amount(Decimal("4200"), unit_text="USD million"),
                         (Decimal("4200000000"), "currency", "USD"))

    def test_magnitude_qualified_unit_still_refused(self):
        with self.assertRaises(sc.SynthesisError):
            sc.SynthesisItem(sc.SOURCED, S.ORIGIN_COMPANY, "A source stated a figure.",
                             provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-x")],
                             unit="USD billion")

    def test_no_fx_mechanism_added(self):
        source = open(os.path.join(REPO_ROOT, "lib", "python", "bops", "quantity.py"),
                      encoding="utf-8").read()
        for token in ("exchange_rate", "fx_rate", "convert_currency"):
            self.assertNotIn(token, source)


class TrustBoundary(unittest.TestCase):

    def test_external_statement_stays_sourced_and_untrusted(self):
        _, statement, _ = build()
        self.assertEqual(statement.kind, sc.SOURCED)
        self.assertEqual(statement.domain, sc.EXTERNAL)
        self.assertEqual(statement.trust, sc.UNTRUSTED)
        self.assertEqual(statement.evidence_class, 3)

    def test_evidence_stays_untrusted_after_establishing_a_dimension(self):
        _, statement, evidence = build()
        self.assertEqual(evidence.trust, "untrusted")
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)
        self.assertEqual(evidence.trust, "untrusted")

    def test_no_verified_flag_anywhere(self):
        result, statement, _ = build()
        self.assertNotIn("verified", json.dumps(result.as_dict(), default=str).lower()
                         .replace("unverified", ""))

    def test_no_recommendation_produced(self):
        result, _, _ = build()
        self.assertEqual(result.as_dict()["recommendations"], [])

    def test_admissibility_grants_no_support_or_confidence_uplift(self):
        _, backed, _ = build()
        _, unbacked, _ = build(provenance=[])
        self.assertEqual(backed.support, unbacked.support)
        self.assertEqual(backed.confidence, unbacked.confidence)


class StrictMode(unittest.TestCase):
    """The opt-in that closes the residual gap for migrated callers."""

    def test_strict_mode_refuses_unfooted_external_dimensions(self):
        _, statement, _ = build(provenance=[], strict=True)
        self.assertTrue(all(v is None for k, v in statement.dimensions.items()
                            if k != "unit" or v is None))
        self.assertIsNone(statement.dimensions["geography"])

    def test_strict_mode_admits_properly_footed_dimensions(self):
        _, statement, _ = build(strict=True)
        self.assertEqual(statement.dimensions["geography"], GEOGRAPHY)
        self.assertEqual(statement.dimensions["currency"], CURRENCY)

    def test_default_is_permissive_so_the_change_is_additive(self):
        result = S.SynthesisSet(subject="default")
        self.assertFalse(result.require_dimension_provenance)

    def test_internal_statements_are_unaffected_by_strict_mode(self):
        result = S.SynthesisSet(subject="internal under strict",
                                require_dimension_provenance=True)
        internal = internal_twin(result)
        self.assertEqual(internal.dimensions["geography"], GEOGRAPHY)
        self.assertEqual(internal.dimensions["methodology"], METHODOLOGY)


class AllowPair(unittest.TestCase):
    """A fully footed external statement may still reach ALLOW against an internal twin."""

    def test_seven_dimensions_compatible_through_the_production_path(self):
        result, external, _ = build(strict=True)
        internal = internal_twin(result)
        record = compat.compare(internal, external)
        self.assertEqual(record["status"], compat.COMPATIBLE)
        self.assertEqual(len(record["matched"]), 7)
        self.assertEqual(record["mismatched"], [])
        self.assertEqual(record["unknown"], [])
        self.assertFalse(record["converted"])
        self.assertTrue(compat.may_combine(record))

    def test_allow_does_not_promote_the_external_statement(self):
        result, external, _ = build(strict=True)
        internal = internal_twin(result)
        S.compare_values(result, internal, external, subject="revenue")
        self.assertEqual(external.trust, sc.UNTRUSTED)
        self.assertEqual(external.kind, sc.SOURCED)

    def test_removing_one_footing_returns_the_pair_to_unknown(self):
        primary = item()
        result = S.SynthesisSet(subject="one footing short",
                                require_dimension_provenance=True)
        S.register_external(result, evidence_set(primary), S.ORIGIN_COMPANY)
        provenance = [f for f in footings(primary.id) if f.dimension != "geography"]
        external = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            metric_definition=DEFINITION, period=PERIOD, geography=GEOGRAPHY,
            scope=SCOPE, methodology=METHODOLOGY, dimension_provenance=provenance)
        internal = internal_twin(result)
        record = compat.compare(internal, external)
        self.assertEqual(record["status"], compat.UNKNOWN)


class Serialisation(unittest.TestCase):

    def test_repeated_serialisation_is_byte_identical(self):
        result, _, _ = build()
        self.assertEqual(result.to_json(indent=2).encode(),
                         result.to_json(indent=2).encode())

    def test_footings_serialise_in_fixed_dimension_order(self):
        _, statement, _ = build()
        order = [e["dimension"] for e in statement.as_dict()["dimension_provenance"]]
        self.assertEqual(order, [d for d in sc.DIMENSIONS if d in order])

    def test_order_is_independent_of_insertion_order(self):
        primary = item()
        forward = footings(primary.id)
        backward = list(reversed(footings(primary.id)))
        a, _, _ = build(provenance=forward)
        b, _, _ = build(provenance=backward)
        self.assertEqual(a.to_json(indent=2), b.to_json(indent=2))

    def test_document_validates_against_the_schema(self):
        result, _, _ = build()
        schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
        document = json.loads(result.to_json())
        self.assertEqual(jsonschema_mini.validate(document, schema), [])

    def test_serialised_footing_carries_no_source_metadata(self):
        _, statement, _ = build()
        for entry in statement.as_dict()["dimension_provenance"]:
            for field in ("source_tier", "trust", "freshness", "retrieved_at",
                          "reference", "source"):
                self.assertNotIn(field, entry)

    def test_resolution_trail_is_serialised_for_audit(self):
        _, statement, _ = build()
        trail = statement.as_dict()["dimension_resolution"]
        self.assertEqual(len(trail), 7)
        self.assertTrue(all("basis" in r for r in trail))


class Vocabulary(unittest.TestCase):

    def test_bases_are_closed(self):
        self.assertEqual(dp.BASES, ("stated", "context", "derived", "asserted"))
        self.assertEqual(dp.ADMISSIBLE_BASES, ("stated", "context", "derived"))

    def test_unknown_basis_refused(self):
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("currency", CURRENCY, "trusted", evidence_id="ev-x")

    def test_unknown_dimension_refused(self):
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("vibe", "good", dp.ASSERTED)

    def test_admissible_basis_requires_an_evidence_id(self):
        for basis in dp.ADMISSIBLE_BASES:
            with self.assertRaises(sc.SynthesisError):
                dp.DimensionProvenance("currency", CURRENCY, basis)

    def test_stated_and_context_require_an_excerpt(self):
        for basis in (dp.STATED, dp.CONTEXT):
            with self.assertRaises(sc.SynthesisError):
                dp.DimensionProvenance("currency", CURRENCY, basis, evidence_id="ev-x")

    def test_derivation_only_on_derived(self):
        with self.assertRaises(sc.SynthesisError):
            dp.DimensionProvenance("currency", CURRENCY, dp.STATED, evidence_id="ev-x",
                                   source_excerpt="USD",
                                   derivation="adr0025.canonical_amount.currency_code")

    def test_non_derivable_dimensions_named_as_data(self):
        self.assertEqual(set(dp.NON_DERIVABLE_DIMENSIONS),
                         {"metric_definition", "period", "geography", "scope",
                          "methodology"})
        self.assertTrue(dp.NEVER_INFERS)

    def test_footings_must_be_objects_not_mappings(self):
        with self.assertRaises(sc.SynthesisError):
            sc.SynthesisItem(sc.SOURCED, S.ORIGIN_COMPANY, "A source stated a figure.",
                             provenance=[sc.ProvenanceRef(sc.P_EVIDENCE, "ev-x")],
                             dimension_provenance=[{"dimension": "currency"}])

    def test_value_must_agree_with_the_statement(self):
        primary = item()
        result = S.SynthesisSet(subject="disagreeing value")
        S.register_external(result, evidence_set(primary), S.ORIGIN_COMPANY)
        statement = S.sourced_statement(
            result, S.ORIGIN_COMPANY, METRIC_TEXT, evidence_ids=[primary.id],
            metric="revenue", observed=Decimal("4.2"), source_unit="USD billion",
            period=PERIOD, scope=SCOPE, geography=GEOGRAPHY,
            dimension_provenance=[dp.DimensionProvenance(
                "geography", "somewhere else", dp.CONTEXT, evidence_id=primary.id,
                source_excerpt="worldwide operations",
                applicability=dict(APPLICABILITY))])
        self.assertIsNone(statement.dimensions["geography"])
        reasons = [r.get("reason") for r in statement.dimension_resolution]
        self.assertIn(dp.VALUE_DISAGREES, reasons)


if __name__ == "__main__":
    unittest.main()
