"""M10.2-R — an internal statement must rest on an internal source.

M10.1 constrained which *kind* a statement may take from the *origin* the caller declared:
an external origin may not be a `FACT`, and an internal origin may not be `SOURCED`. The
M10.2 live verification showed that this is necessary and not sufficient. A caller that
declares `ORIGIN_FINANCIAL` while attaching only `P_EVIDENCE` provenance satisfied the
kind/origin rule and produced an item serialised as `kind: FACT`, `domain: internal`,
`trust: internal`, `evidence_class: 1` — a class-1 internal fact whose entire chain was one
tier-C commercial research house. Nothing downstream could tell it apart from a figure
measured from the user's own data, which is the one distinction the synthesis layer exists
to keep.

The remedy is to read the chain rather than the label: `SynthesisSet.add()` now refuses an
internal `FACT` or `CALCULATION` unless at least one attached reference **resolves against
this set's registries** to an internal source. Resolution is the point — `domain`, `origin`,
`trust`, `evidence_class` and any tier carried on the cited object are all caller- or
payload-influenced, so none of them is consulted.

The escalation probes from the M10.2 report are carried here verbatim as regression tests
and must never be weakened: `test_live_shaped_escalation_*` are the three variants that
were accepted before the fix.
"""

import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import jsonschema_mini                            # noqa: E402
from bops import synthesis as S                             # noqa: E402

from fixtures.build_synthesis_fixtures import (            # noqa: E402
    TEST_DATASET as DATASET, dataset_ref, demo_evidence, evidence_set_with,
    internal_margin, new_set,
)

SCHEMA_PATH = os.path.join(REPO_ROOT, "lib", "schemas", "synthesis.schema.json")


def _set_with_evidence():
    """A set holding one registered dataset and one registered external evidence item."""
    result = new_set()
    item = demo_evidence()
    S.register_external(result, evidence_set_with(item), S.ORIGIN_INDUSTRY)
    return result, item


def _external_ref(item):
    return S.ProvenanceRef(S.P_EVIDENCE, item.id)


class InternalFootingRequired(unittest.TestCase):
    """The invariant itself: internal FACT/CALCULATION needs an internal reference."""

    def test_internal_fact_with_internal_provenance_is_accepted(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.FACT, S.ORIGIN_FINANCIAL, "The dataset covers 24 monthly periods.",
            provenance=[dataset_ref()]))
        self.assertEqual(item.kind, S.FACT)
        self.assertEqual(item.domain, S.INTERNAL)
        self.assertTrue(item.internal_refs())

    def test_internal_calculation_with_internal_provenance_is_accepted(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_KPI, "Gross margin is 34.9%.",
            provenance=[dataset_ref()], basis="(revenue - cost) / revenue"))
        self.assertEqual(item.kind, S.CALCULATION)
        self.assertTrue(item.internal_refs())

    def test_live_shaped_escalation_nonmaterial_internal_fact_is_refused(self):
        """M10.2 probe (a). Accepted before the fix; must always be refused now."""
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError) as caught:
            result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our industry is USD 1,043.12 billion in 2026.",
                provenance=[_external_ref(evidence)]))
        self.assertIn("internal FACT", str(caught.exception))

    def test_live_shaped_escalation_material_internal_fact_is_refused(self):
        """M10.2 probe (b). Materiality must not buy an exemption."""
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError):
            result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our industry is USD 1,043.12 billion in 2026.",
                provenance=[_external_ref(evidence)],
                materiality={"outcome": "material", "reason": "headline figure"}))

    def test_live_shaped_escalation_internal_calculation_is_refused(self):
        """M10.2 probe (c). The same hole existed for class 4."""
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError):
            result.add(S.SynthesisItem(
                S.CALCULATION, S.ORIGIN_KPI, "Industry size is USD 1,043.12 billion.",
                provenance=[_external_ref(evidence)], basis="sourced figure"))

    def test_claim_provenance_is_external_footing_too(self):
        """`P_CLAIM` is a candidate external claim, not an internal source."""
        result, evidence = _set_with_evidence()
        claims = result.register_claims([
            {"statement": "A source states the market was USD 282.8bn.",
             "evidence_id": evidence.id}])
        with self.assertRaises(S.SynthesisError):
            result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our market was USD 282.8bn.",
                provenance=[S.ProvenanceRef(S.P_CLAIM, claims[0]["claim_id"])]))

    def test_unavailable_only_provenance_cannot_found_an_internal_fact(self):
        """Provenance that asserts nothing is not footing for a class-1 statement."""
        result = new_set()
        with self.assertRaises(S.SynthesisError):
            result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Revenue was USD 3,467,850.16.",
                provenance=[S.ProvenanceRef.unavailable("the source system was offline")]))

    def test_mixed_provenance_is_accepted_when_an_internal_reference_is_present(self):
        """The stated rule is *at least one* internal reference, not *only* internal ones.

        This is the existing policy made explicit rather than a new permission: an item
        that genuinely rests on the user's data does not stop doing so because it also
        cites a source alongside it.
        """
        result, evidence = _set_with_evidence()
        item = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_FINANCIAL, "Gross margin is 34.9%.",
            provenance=[_external_ref(evidence), dataset_ref()],
            basis="(revenue - cost) / revenue"))
        self.assertEqual(len(item.internal_refs()), 1)
        self.assertEqual(len(item.external_refs()), 1)

    def test_declared_trust_and_confidence_cannot_buy_an_exemption(self):
        """Derived fields are refused outright, so they cannot accompany the attempt."""
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError):
            S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our industry is USD 1,043.12 billion.",
                provenance=[_external_ref(evidence)],
                trust="internal", confidence="HIGH")

    def test_footing_is_checked_against_the_registry_not_the_reference(self):
        """An internal-looking reference to an object this set never held is refused.

        Catches the obvious bypass: dressing an external chain as `P_FINDING` and hoping
        the kind alone satisfies the check.
        """
        result, _evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError) as caught:
            result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Revenue was USD 3,467,850.16.",
                provenance=[S.ProvenanceRef(S.P_FINDING, "financial.kpi.invented")]))
        self.assertIn("no registered source object", str(caught.exception))

    def test_kinds_requiring_internal_footing_are_exactly_fact_and_calculation(self):
        self.assertEqual(set(S.INTERNALLY_FOOTED_KINDS), {S.FACT, S.CALCULATION})

    def test_internal_provenance_is_the_complement_of_external(self):
        self.assertEqual(
            set(S.INTERNAL_PROVENANCE) | set(S.contract.EXTERNAL_PROVENANCE),
            set(S.contract.RESOLVABLE_KINDS))
        self.assertFalse(set(S.INTERNAL_PROVENANCE) & set(S.contract.EXTERNAL_PROVENANCE))
        self.assertNotIn(S.P_UNAVAILABLE, S.INTERNAL_PROVENANCE)


class DomainConstraintStillHolds(unittest.TestCase):
    """The M10.1 kind/origin rule is unchanged; the new check is additional."""

    def test_external_origin_fact_is_refused(self):
        with self.assertRaises(S.SynthesisError) as caught:
            S.SynthesisItem(S.FACT, S.ORIGIN_INDUSTRY, "The industry grew 4%.",
                            provenance=[dataset_ref()])
        self.assertIn("may not be a FACT", str(caught.exception))

    def test_external_origin_calculation_is_refused(self):
        with self.assertRaises(S.SynthesisError):
            S.SynthesisItem(S.CALCULATION, S.ORIGIN_MARKET, "The market grew 4%.",
                            provenance=[dataset_ref()], basis="source arithmetic")

    def test_sourced_statement_still_refuses_an_internal_origin(self):
        result, evidence = _set_with_evidence()
        with self.assertRaises(S.SynthesisError) as caught:
            S.sourced_statement(result, S.ORIGIN_FINANCIAL, "A source said something.",
                                evidence_ids=[evidence.id])
        self.assertIn("must have an external origin", str(caught.exception))

    def test_recommendation_remains_reserved(self):
        with self.assertRaises(S.SynthesisError):
            S.SynthesisItem(S.RECOMMENDATION, S.ORIGIN_INDUSTRY, "Enter the industry.",
                            provenance=[dataset_ref()])


class LegitimatePathsUnaffected(unittest.TestCase):
    """Every production route into the set must still work."""

    def test_from_analysis_set_still_produces_calculations(self):
        result = new_set()
        produced = S.from_analysis_set(result, internal_margin(), S.ORIGIN_FINANCIAL,
                                       dataset_id=DATASET)
        self.assertTrue(produced)
        for item in produced:
            self.assertEqual(item.domain, S.INTERNAL)
            self.assertTrue(item.internal_refs(),
                            "engine findings must carry internal footing")

    def test_sourced_statement_still_produces_external_sourced(self):
        result, evidence = _set_with_evidence()
        item = S.sourced_statement(result, S.ORIGIN_INDUSTRY,
                                   "A source reports the market at USD 282.8bn.",
                                   evidence_ids=[evidence.id])
        self.assertEqual(item.kind, S.SOURCED)
        self.assertEqual(item.domain, S.EXTERNAL)

    def test_interpretation_over_external_statements_is_unaffected(self):
        result, evidence = _set_with_evidence()
        sourced = S.sourced_statement(result, S.ORIGIN_INDUSTRY,
                                      "A source reports the market at USD 282.8bn.",
                                      evidence_ids=[evidence.id])
        reading = S.interpretation(result, S.ORIGIN_INDUSTRY,
                                   "The sizing evidence is thin.",
                                   supports=[sourced.id])
        self.assertEqual(reading.kind, S.INTERPRETATION)

    def test_assumption_with_unavailable_provenance_is_unaffected(self):
        result = new_set()
        item = S.assumption(result, S.ORIGIN_FORECAST, "Seasonality is stable.",
                            detail="modelled, not measured")
        self.assertEqual(item.kind, S.ASSUMPTION)

    def test_candidate_claims_remain_unverified(self):
        result, evidence = _set_with_evidence()
        claims = result.register_claims([
            {"statement": "A source states the market was USD 282.8bn.",
             "evidence_id": evidence.id}])
        self.assertEqual(claims[0]["status"], "candidate")
        self.assertIs(claims[0]["verified"], False)


class SchemaMirrorsTheRuntimeRule(unittest.TestCase):
    """The schema is defence in depth for records that never met the object model."""

    @classmethod
    def setUpClass(cls):
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            cls.schema = json.load(handle)
        cls.item_schema = cls.schema["definitions"]["item"]

    def _record(self, **over):
        record = {"synthesis_id": "sy-0123456789ab", "evidence_class": 1,
                  "origin": "financial", "domain": "internal", "trust": "internal",
                  "statement": "s"}
        record.update(over)
        return record

    def _validate(self, record):
        return jsonschema_mini.validate(record, self.item_schema, root=self.schema)

    def test_schema_uses_only_supported_keywords(self):
        self.assertEqual(jsonschema_mini.unsupported_keywords(self.schema), set())

    def test_schema_rejects_internal_fact_with_external_only_provenance(self):
        self.assertTrue(self._validate(self._record(
            kind="FACT", provenance=[{"kind": "evidence", "ref_id": "ev-1"}])))

    def test_schema_rejects_internal_calculation_with_external_only_provenance(self):
        self.assertTrue(self._validate(self._record(
            kind="CALCULATION", provenance=[{"kind": "claim", "ref_id": "cl-1"}])))

    def test_schema_rejects_internal_fact_with_unavailable_only_provenance(self):
        self.assertTrue(self._validate(self._record(
            kind="FACT", provenance=[{"kind": "unavailable", "detail": "none"}])))

    def test_schema_accepts_internal_fact_with_internal_provenance(self):
        self.assertEqual(self._validate(self._record(
            kind="FACT", provenance=[{"kind": "finding", "ref_id": "f-1"}])), [])

    def test_schema_accepts_mixed_provenance_with_an_internal_reference(self):
        self.assertEqual(self._validate(self._record(
            kind="CALCULATION",
            provenance=[{"kind": "evidence", "ref_id": "ev-1"},
                        {"kind": "finding", "ref_id": "f-1"}])), [])

    def test_schema_accepts_external_sourced(self):
        self.assertEqual(self._validate(self._record(
            kind="SOURCED", domain="external", origin="industry", trust="untrusted",
            evidence_class=3,
            provenance=[{"kind": "evidence", "ref_id": "ev-1"}])), [])

    def test_schema_leaves_interpretation_and_assumption_unconstrained(self):
        self.assertEqual(self._validate(self._record(
            kind="INTERPRETATION", evidence_class=5,
            provenance=[{"kind": "evidence", "ref_id": "ev-1"}])), [])
        self.assertEqual(self._validate(self._record(
            kind="ASSUMPTION", evidence_class=6,
            provenance=[{"kind": "unavailable", "detail": "modelled"}])), [])


class SerialisationPreservesValidProvenance(unittest.TestCase):

    def test_round_trip_keeps_internal_footing_visible(self):
        result = new_set()
        S.from_analysis_set(result, internal_margin(), S.ORIGIN_FINANCIAL,
                            dataset_id=DATASET)
        record = json.loads(result.to_json())
        reloaded = S.load(record)
        self.assertEqual([i.id for i in reloaded], [i.id for i in result.items])
        for original, restored in zip(result.items, reloaded):
            self.assertEqual([(r.kind, r.ref_id) for r in original.provenance],
                             [(r.kind, r.ref_id) for r in restored.provenance])
            self.assertTrue(restored.internal_refs())

    def test_serialised_set_validates_against_the_tightened_schema(self):
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            schema = json.load(handle)
        result = new_set()
        S.from_analysis_set(result, internal_margin(), S.ORIGIN_FINANCIAL,
                            dataset_id=DATASET)
        self.assertEqual(jsonschema_mini.validate(json.loads(result.to_json()), schema),
                         [])


if __name__ == "__main__":
    unittest.main()
