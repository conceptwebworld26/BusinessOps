# -*- coding: utf-8 -*-
"""M10.3.2 — Strategy Recommendations: class-7 records grounded in a synthesis set (ADR-0031).

`bops.strategy` is the engine, `bops-strategy-recommendations` the skill and `/strategy-analysis`
the command. These tests pin the contract ADR-0031 decided, and they start where a real run
starts: `commands.run()` over the shipped synthetic demo file, genuine `BOPS-REC/1` replies
closed through `research.close_retrieval_object()`, and the existing synthesis translators.

What gets the most attention:

* **Evidence is resolution, never text.** Every id resolves in one genuine strict set through
  `synthesis.grounding`, the single home the SWOT consumer also uses. Fakes, out-of-set ids,
  assumptions, recommendations and unsupported statements are refused.
* **Confidence is derived.** No field exists to author it; it is `confidence.combine()` over the
  reason codes the set already derived.
* **Figures are quoted, never produced.** `figure_tokens()` and `require_grounded()` are tested
  as a rule, not by a handful of examples.
* **Nothing re-enters synthesis.** `register_claims()` refuses every spelling of a
  recommendation, and the set's `recommendations` stays empty.
* **Nothing is ranked, scored or executed** — asserted on the structured output and the schema.

**Every fixture is synthetic.** The internal side is `assets/demo-data/northwind_sales.csv`,
generated synthetic data; the external side is invented sentences on `.example.invalid` hosts.
Nothing reaches a network or dispatches a scout.
"""

import io
import json
import os
import re
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import commands as C                              # noqa: E402
from bops import context as context_mod                     # noqa: E402
from bops import evidence as evidence_mod                   # noqa: E402
from bops import jsonschema_mini                            # noqa: E402
from bops import research as R                              # noqa: E402
from bops import strategy                                   # noqa: E402
from bops import swot                                       # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.research import scout as scout_mod                # noqa: E402
from bops.synthesis import confidence as conf_mod           # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402
from bops.synthesis import grounding                        # noqa: E402
from bops.synthesis import limitations as lim_mod           # noqa: E402
from bops.synthesis import merge as merge_mod               # noqa: E402

LIB = os.path.join(REPO_ROOT, "lib", "python", "bops")
STRATEGY_PY = os.path.join(LIB, "strategy.py")
SWOT_PY = os.path.join(LIB, "swot.py")
GROUNDING_PY = os.path.join(LIB, "synthesis", "grounding.py")
MERGE_PY = os.path.join(LIB, "synthesis", "merge.py")
STRATEGY_SCHEMA = os.path.join(REPO_ROOT, "lib", "schemas", "strategy.schema.json")
LEDGER_SCHEMA = os.path.join(REPO_ROOT, "lib", "schemas", "claim_ledger.schema.json")
SYNTHESIS_SCHEMA = os.path.join(REPO_ROOT, "lib", "schemas", "synthesis.schema.json")
SKILL_MD = os.path.join(REPO_ROOT, "skills", "bops-strategy-recommendations", "SKILL.md")
COMMAND_MD = os.path.join(REPO_ROOT, "commands", "strategy-analysis.md")
DEMO = os.path.join(REPO_ROOT, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO_ROOT, "assets", "demo-data", "business_context.json")

AS_OF = "2026-09-16"
DATASET_ID = "ds-m1032-demo"
PUBLISHED = "2026-02-10"

# ---------------------------------------------------------------------------
# Internal half
# ---------------------------------------------------------------------------

DOMAIN_ORIGINS = (("sales", S.ORIGIN_SALES), ("customer", S.ORIGIN_CUSTOMER),
                  ("product", S.ORIGIN_PRODUCT), ("financial", S.ORIGIN_FINANCIAL))

_RUNS = {}


def shared_run(command_id="business-health"):
    """A cached genuine `CommandResult`. No test mutates a shared run."""
    if command_id not in _RUNS:
        _RUNS[command_id] = C.run(command_id, source=DEMO)
    return _RUNS[command_id]


def strict_set(subject="Northwind demo", **fields):
    return S.SynthesisSet(subject=subject, require_dimension_provenance=True, **fields)


def add_internal(synthesis, run=None, domains=("sales", "product", "financial")):
    run = shared_run() if run is None else run
    for domain, origin in DOMAIN_ORIGINS:
        if domain in domains and domain in run.analysis_keys:
            C.internal_statements(synthesis, run, origin, DATASET_ID, domains=[domain])
    return synthesis


def find(synthesis, prefix, origin=None):
    matches = [item for item in synthesis.items if item.statement.startswith(prefix)
               and (origin is None or item.origin == origin)]
    assert len(matches) == 1, (prefix, [m.statement for m in matches])
    return matches[0]


REVENUE_GROWTH = "Revenue growth is 69.72%."
MARGIN_DECLINE = "Average gross margin moved from 37.26% to 34.41%"
GROSS_PROFIT_GROWTH = "Gross profit moved from USD 482195.91"
LEGACY_DECLINE = "Legacy Crates moved from USD 98235.96"

# ---------------------------------------------------------------------------
# External half
# ---------------------------------------------------------------------------

MARKET_OPERATION = "strategy-analysis-cold-chain-market-trends-2026-09-16"
MARKET_SUBJECT = "cold chain logistics market"
MARKET_TERMS = {"industry": "cold chain logistics", "geographic_market": "United Kingdom",
                "period": "2025"}
DEMAND_DOC = "https://market-outlook.example.invalid/cold-chain-2025.htm"
PRICE_DOC = "https://trade-press.example.invalid/chilled-price-cut.htm"
CAPACITY_DOC = "https://capacity-watch.example.invalid/pallet-positions.htm"


def record(content, reference, source, title, claim_kind="positioning"):
    return {"source": source, "reference": reference, "title": title,
            "publication_date": PUBLISHED, "source_type": "industry_report",
            "content": content, "claim_kind": claim_kind}


DEMAND = record(
    "SYNTHETIC market outlook: demand for temperature-controlled warehouse capacity in the "
    "United Kingdom increased during 2025, led by online grocery volumes.",
    DEMAND_DOC, "SYNTHETIC market outlook (test fixture, not a real source)",
    "Cold chain market outlook 2025")
PRICE_CUT = record(
    "SYNTHETIC trade press: a competing operator launched a lower-priced chilled storage "
    "service across the United Kingdom in March 2026.",
    PRICE_DOC, "SYNTHETIC trade press (test fixture, not a real source)",
    "Competitor launches lower-priced chilled storage")
CAPACITY = record(
    "SYNTHETIC capacity watch: 3,500 new chilled pallet positions opened in the United "
    "Kingdom in 2025.",
    CAPACITY_DOC, "SYNTHETIC capacity watch (test fixture, not a real source)",
    "Chilled pallet positions 2025")

DEMAND_TEXT = ("The market outlook reports that UK demand for temperature-controlled "
               "warehouse capacity increased during 2025.")
PRICE_TEXT = ("Trade press reports that a competing operator launched a lower-priced chilled "
              "storage service in the UK in March 2026.")
CAPACITY_TEXT = ("A capacity watch reports 3,500 new chilled pallet positions opened in the "
                 "UK in 2025.")


def reply(records, operation):
    lines = ["%s %s %s" % (scout_mod.RECORD_TOKEN, operation, json.dumps(entry))
             for entry in records]
    lines.append("%s %s %d" % (scout_mod.END_TOKEN, operation, len(records)))
    return "\n".join(lines)


def open_market_brief():
    return R.open_retrieval(MARKET_SUBJECT, R.MARKET, intent=R.TRENDS,
                            public_terms=dict(MARKET_TERMS), operation=MARKET_OPERATION)


def close_market(records=None, conflicts=None):
    entries = [DEMAND, PRICE_CUT, CAPACITY] if records is None else records
    return R.close_retrieval_object(reply(entries, MARKET_OPERATION), MARKET_SUBJECT, R.MARKET,
                                    as_of=AS_OF, intent=R.TRENDS,
                                    public_terms=dict(MARKET_TERMS),
                                    operation=MARKET_OPERATION, conflicts=conflicts)


def evidence_for(evidence, reference):
    return [item for item in evidence.items if item.reference == reference][0]


def add_external(synthesis, retrieval=None, materiality=None):
    retrieval = close_market() if retrieval is None else retrieval
    evidence = S.evidence_from_retrieval(retrieval)
    S.register_external(synthesis, evidence, S.ORIGIN_MARKET)
    demand = S.sourced_statement(synthesis, S.ORIGIN_MARKET, DEMAND_TEXT,
                                 evidence_ids=[evidence_for(evidence, DEMAND_DOC).id],
                                 materiality=materiality)
    price = S.sourced_statement(synthesis, S.ORIGIN_MARKET, PRICE_TEXT,
                                evidence_ids=[evidence_for(evidence, PRICE_DOC).id])
    capacity = S.sourced_statement(synthesis, S.ORIGIN_MARKET, CAPACITY_TEXT,
                                   evidence_ids=[evidence_for(evidence, CAPACITY_DOC).id])
    return demand, price, capacity


INDUSTRY_OPERATION = "strategy-analysis-cold-chain-industry-benchmark-2026-09-16"
BENCH_DOC = "https://sector-statistics.example.invalid/logistics-revenue-2025.htm"
DEFINITION = "net sales of cold chain logistics operators"
PERIOD = "calendar year 2025"
GEOGRAPHY = "worldwide"
SCOPE = "whole business, all segments"
METHODOLOGY = "sum of reported operator revenue"
INTERNAL_DIMENSIONS = {"metric_definition": DEFINITION, "period": PERIOD,
                       "geography": GEOGRAPHY, "scope": SCOPE, "methodology": METHODOLOGY}
BENCHMARK = ("The typical cold chain logistics operator, on a definition of %s, reported "
             "revenue of USD 3.47 million in %s. The benchmark covers %s operations measured "
             "as %s and was compiled on a %s."
             % (DEFINITION, PERIOD, GEOGRAPHY, SCOPE, METHODOLOGY))
BENCHMARK_TEXT = "The benchmark reports operator revenue of USD 3.47 million for %s." % PERIOD


def close_industry():
    entry = {"source": "SYNTHETIC sector statistics (test fixture, not a real source)",
             "reference": BENCH_DOC, "title": "Cold chain operator revenue benchmark, 2025",
             "publication_date": PUBLISHED, "source_type": "official_statistics",
             "content": BENCHMARK, "claim_kind": "financials"}
    return R.close_retrieval_object(
        reply([entry], INDUSTRY_OPERATION), "cold chain logistics operator revenue",
        R.INDUSTRY, as_of=AS_OF, intent=R.BENCHMARK,
        public_terms={"industry": "cold chain logistics", "period": "2025"},
        operation=INDUSTRY_OPERATION)


def claims(geography_excerpt=None):
    return {
        "metric_definition": (DEFINITION, "on a definition of %s" % DEFINITION),
        "period": (PERIOD, "in %s" % PERIOD),
        "currency": ("USD", "revenue of USD 3.47 million"),
        "geography": (GEOGRAPHY, geography_excerpt or "covers %s operations" % GEOGRAPHY),
        "scope": (SCOPE, "measured as %s" % SCOPE),
        "methodology": (METHODOLOGY, "compiled on a %s" % METHODOLOGY),
    }


def join(internal_dimensions=None, stated=None, synthesis=None):
    retrieval = close_industry()
    return C.local_join(
        shared_run("profitability-analysis"), retrieval, S.ORIGIN_INDUSTRY, BENCHMARK_TEXT,
        retrieval["evidence_set"].items[0].id, dataset_id=DATASET_ID,
        internal_metric="revenue",
        internal_dimensions=(INTERNAL_DIMENSIONS if internal_dimensions is None
                             else internal_dimensions),
        stated=claims() if stated is None else stated, synthesis=synthesis,
        metric="revenue", observed=Decimal("3.47"), source_unit="USD million")


# ---------------------------------------------------------------------------
# Common shapes
# ---------------------------------------------------------------------------

def mixed_set(**fields):
    """Internal and external statements, two readings and one assumption, in one strict set."""
    synthesis = add_internal(strict_set(**fields))
    demand, price, capacity = add_external(synthesis)
    growth = find(synthesis, REVENUE_GROWTH, S.ORIGIN_SALES)
    margin = find(synthesis, MARGIN_DECLINE)
    tailwind = S.interpretation(
        synthesis, S.ORIGIN_MARKET,
        "Rising UK demand for temperature-controlled capacity coincides with the business's "
        "revenue growth over the same period.", supports=[growth.id, demand.id])
    pressure = S.interpretation(
        synthesis, S.ORIGIN_MARKET,
        "A lower-priced competing chilled storage service arrived while the business's "
        "average gross margin was already declining.", supports=[margin.id, price.id])
    assumed = S.assumption(synthesis, S.ORIGIN_FINANCIAL,
                           "Input costs are assumed to stay flat next year.",
                           "No cost forecast exists in the supplied data.")
    return synthesis, {"growth": growth, "margin": margin, "demand": demand, "price": price,
                       "capacity": capacity, "tailwind": tailwind, "pressure": pressure,
                       "assumed": assumed,
                       "gross_profit": find(synthesis, GROSS_PROFIT_GROWTH),
                       "legacy": find(synthesis, LEGACY_DECLINE, S.ORIGIN_PRODUCT)}


def proposal(evidence, **overrides):
    record_ = {
        "action": "Review pricing on the product lines behind the gross margin decline.",
        "evidence": [e if isinstance(e, str) else e.id for e in evidence],
        "rationale": "The cited statements show the margin moving down over the period.",
        "expected_benefit": "A clearer view of which lines drove the decline.",
        "risks": ["Price changes may reduce order volume."],
        "dependencies": [{"text": "The cited evidence remains current and correctly scoped."}],
    }
    record_.update(overrides)
    return record_


def schema_errors(record_, schema_path=STRATEGY_SCHEMA):
    with io.open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)
    return jsonschema_mini.validate(json.loads(json.dumps(record_, default=str)), schema)


def all_keys(value):
    found = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            found.add(key)
            found |= all_keys(inner)
    elif isinstance(value, (list, tuple)):
        for inner in value:
            found |= all_keys(inner)
    return found


def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def code(path):
    """Executable source with docstrings and comments removed, for invariant scans."""
    text = re.sub(r'""".*?"""', "", read(path), flags=re.S)
    return "\n".join(line.split("#")[0] for line in text.split("\n"))


def frontmatter(text):
    return text.split("---", 2)[1]


# =======================================================================================
# A. Positive paths
# =======================================================================================

class SingleRecommendation(unittest.TestCase):
    """A — one recommendation, one genuine strict set, evidence resolved."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.before = cls.synthesis.to_json()
        cls.result = strategy.build(cls.synthesis, [proposal([cls.parts["margin"]])])
        cls.record = cls.result.recommendations[0]
        cls.output = cls.result.as_dict()

    def test_one_recommendation_is_issued_with_class_seven_identity(self):
        self.assertEqual(len(self.result.recommendations), 1)
        self.assertEqual(self.record["provenance_class"], evidence_mod.RECOMMENDATION)
        self.assertEqual(self.record["label"], "RECOMMENDATION")
        self.assertEqual(self.record["issued_by"], strategy.ISSUED_BY)
        self.assertEqual(self.record["recommendation_id"],
                         strategy.recommendation_id(self.record["action"],
                                                    self.record["evidence"]))

    def test_the_authored_fields_are_carried_exactly(self):
        authored = proposal([self.parts["margin"]])
        for name in ("action", "evidence", "rationale", "expected_benefit", "risks"):
            self.assertEqual(self.record[name], authored[name])
        self.assertEqual(self.record["dependencies"],
                         [{"text": authored["dependencies"][0]["text"],
                           "assumption_id": None}])

    def test_evidence_resolves_to_the_statement_in_the_set(self):
        detail = self.record["evidence_detail"][0]
        self.assertEqual(detail["synthesis_id"], self.parts["margin"].id)
        self.assertEqual(detail["statement"], self.parts["margin"].statement)
        self.assertEqual(detail["kind"], S.CALCULATION)
        self.assertEqual(detail["evidence_class"], 4)
        self.assertTrue(all(entry["resolved"] for entry in detail["chain"]))

    def test_the_result_sits_beside_the_set_and_changes_nothing(self):
        self.assertIs(self.result.synthesis, self.synthesis)
        self.assertTrue(self.result.is_bound_to(self.synthesis))
        self.assertEqual(self.synthesis.to_json(), self.before)
        self.assertEqual(self.synthesis.recommendations, [])
        self.assertEqual(json.loads(self.synthesis.to_json())["recommendations"], [])

    def test_the_output_validates_against_the_strategy_schema(self):
        self.assertEqual(schema_errors(self.output), [])
        self.assertIsNone(self.output["empty_state"])

    def test_the_class_seven_claim_validates_against_the_ledger_schema(self):
        ledger = evidence_mod.Ledger()
        self.result.record_in(ledger)
        document = {"schema_version": "1.0.0",
                    "claims": [claim.as_dict() for claim in ledger.claims]}
        self.assertEqual(schema_errors(document, LEDGER_SCHEMA), [])
        claim = ledger.claims[0]
        self.assertEqual(claim.statement, self.record["action"])
        self.assertEqual(claim.confidence, self.record["confidence"])
        self.assertEqual(claim.based_on, self.record["evidence"])


class MultipleRecommendations(unittest.TestCase):
    """B — several recommendations, deterministic order that is not a ranking."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        p = cls.parts
        cls.proposals = [
            proposal([p["demand"]], action="Assess storage capacity against the reported "
                                           "UK demand."),
            proposal([p["margin"]]),
            proposal([p["legacy"]], action="Review whether the Legacy Crates line still "
                                           "fits the range."),
        ]
        cls.result = strategy.build(cls.synthesis, cls.proposals)

    def test_all_are_issued_in_set_order_of_first_evidence(self):
        order = [item.id for item in self.synthesis.items]
        firsts = [min(order.index(e) for e in r["evidence"])
                  for r in self.result.recommendations]
        self.assertEqual(firsts, sorted(firsts))
        self.assertEqual(len(self.result.recommendations), 3)

    def test_input_order_does_not_change_the_result(self):
        reversed_ = strategy.build(self.synthesis, list(reversed(self.proposals)))
        self.assertEqual(reversed_.to_json(), self.result.to_json())

    def test_order_is_stated_not_to_be_a_ranking(self):
        output = self.result.as_dict()
        self.assertIn("not a ranking", output["order_note"])
        self.assertIn(strategy.ORDER_NOTE, strategy.render(self.result))

    def test_the_same_recommendation_twice_is_refused(self):
        with self.assertRaises(strategy.StrategyError):
            strategy.build(self.synthesis, [self.proposals[0], dict(self.proposals[0])])


class MixedEvidence(unittest.TestCase):
    """C — internal and external evidence together, each keeping its own standing."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.record = strategy.build(cls.synthesis, [proposal(
            [cls.parts["growth"], cls.parts["demand"]],
            action="Assess storage capacity against reported UK demand and internal growth.",
            rationale="Internal revenue growth and external demand growth point the same "
                      "way.")]).recommendations[0]

    def test_both_domains_are_recorded(self):
        self.assertEqual(self.record["rests_on"], [S.EXTERNAL, S.INTERNAL])

    def test_each_statement_keeps_its_own_kind_trust_and_class(self):
        details = dict((d["synthesis_id"], d) for d in self.record["evidence_detail"])
        internal = details[self.parts["growth"].id]
        external = details[self.parts["demand"].id]
        self.assertEqual((internal["kind"], internal["domain"], internal["trust"],
                          internal["evidence_class"]),
                         (S.CALCULATION, S.INTERNAL, "internal", 4))
        self.assertEqual((external["kind"], external["domain"], external["trust"],
                          external["evidence_class"]),
                         (S.SOURCED, S.EXTERNAL, sc.UNTRUSTED, 3))

    def test_the_weaker_leg_sets_support(self):
        self.assertEqual(self.record["support"], S.PARTIALLY_SUPPORTED)


class InterpretationEvidence(unittest.TestCase):
    """D — an interpretation is evidence only through the shared grounding checks."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.record = strategy.build(cls.synthesis, [proposal(
            [cls.parts["tailwind"]],
            action="Assess storage capacity against the demand trend the reading "
                   "describes.")]).recommendations[0]

    def test_it_is_accepted_and_its_verified_supports_are_listed(self):
        detail = self.record["evidence_detail"][0]
        self.assertEqual(detail["kind"], S.INTERPRETATION)
        self.assertEqual(sorted(s["synthesis_id"] for s in detail["supports"]),
                         sorted([self.parts["growth"].id, self.parts["demand"].id]))
        self.assertEqual(self.record["rests_on"], [S.EXTERNAL, S.INTERNAL])

    def test_the_engine_reads_interpretations_only_through_grounding(self):
        body = code(STRATEGY_PY)
        self.assertIn("grounding.evidence_domains", body)
        self.assertIn("grounding.interpretation_supports", body)
        self.assertNotIn("merge_mod", body)
        self.assertNotIn("from .synthesis import merge", body)

    def test_a_forged_interpretation_is_refused_with_the_shared_refusal(self):
        synthesis = add_internal(strict_set(), domains=("financial", "product"))
        margin = find(synthesis, MARGIN_DECLINE)
        legacy = find(synthesis, LEGACY_DECLINE, S.ORIGIN_PRODUCT)
        forged = synthesis.add(sc.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_FINANCIAL, "Margin weakness is broad-based.",
            provenance=list(legacy.provenance),
            notes=["%s%s" % (merge_mod.RESTS_ON, margin.id)]))
        with self.assertRaises(strategy.StrategyError) as caught:
            strategy.build(synthesis, [proposal([forged])])
        self.assertIn("do not account for", str(caught.exception))


class AssumptionDependency(unittest.TestCase):
    """E — an assumption is named by a dependency, never cited as evidence."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.record = strategy.build(cls.synthesis, [proposal(
            [cls.parts["margin"]],
            dependencies=[{"text": "Input costs behave as assumed.",
                           "assumption_id": cls.parts["assumed"].id}])]).recommendations[0]

    def test_the_assumption_is_disclosed_and_not_evidence(self):
        self.assertEqual([a["synthesis_id"] for a in self.record["assumptions"]],
                         [self.parts["assumed"].id])
        self.assertNotIn(self.parts["assumed"].id, self.record["evidence"])
        self.assertEqual([d["synthesis_id"] for d in self.record["evidence_detail"]],
                         [self.parts["margin"].id])

    def test_it_makes_the_recommendation_low_through_existing_codes(self):
        self.assertEqual(self.record["confidence"], S.LOW)
        for code_ in (conf_mod.PROVENANCE_UNAVAILABLE, conf_mod.INSUFFICIENT_EVIDENCE):
            self.assertIn(code_, self.record["confidence_reasons"])

    def test_the_dependency_keeps_its_assumption_reference(self):
        self.assertEqual(self.record["dependencies"][0]["assumption_id"],
                         self.parts["assumed"].id)


class ConfidenceDerivation(unittest.TestCase):
    """F — `confidence.combine()` over the cited statements' own reason codes."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()

    def build(self, evidence, **overrides):
        return strategy.build(self.synthesis,
                              [proposal(evidence, **overrides)]).recommendations[0]

    def expected(self, items):
        return conf_mod.combine([conf_mod.assess(i.confidence_detail["reasons"])
                                 for i in items])

    def test_all_high_evidence_is_high(self):
        record_ = self.build([self.parts["margin"], self.parts["legacy"]])
        self.assertEqual(self.parts["margin"].confidence, S.HIGH)
        self.assertEqual(record_["confidence"], S.HIGH)
        self.assertEqual(record_["confidence_reasons"], [])

    def test_the_weakest_statement_sets_the_level_and_reasons_pool(self):
        items = [self.parts["margin"], self.parts["demand"]]
        record_ = self.build(items, action="Assess pricing against reported UK demand.")
        expected = self.expected(items)
        self.assertEqual(record_["confidence"], expected.level)
        self.assertEqual(record_["confidence"], S.MEDIUM)
        self.assertEqual(record_["confidence_reasons"], list(expected.reasons))
        self.assertIn(conf_mod.TIER_C_ONLY, record_["confidence_reasons"])

    def test_every_reason_is_an_existing_code(self):
        record_ = self.build([self.parts["margin"], self.parts["demand"]],
                             action="Assess pricing against reported UK demand.",
                             dependencies=[{"text": "Input costs behave as assumed.",
                                            "assumption_id": self.parts["assumed"].id}])
        self.assertTrue(set(record_["confidence_reasons"]) <= set(conf_mod.REASON_CODES))
        self.assertIn(record_["confidence"], conf_mod.LEVELS)

    def test_a_data_quality_warning_makes_it_low(self):
        synthesis = add_internal(strict_set(quality_grade="WARNING"), domains=("financial",))
        record_ = strategy.build(synthesis, [proposal(
            [find(synthesis, MARGIN_DECLINE)])]).recommendations[0]
        self.assertEqual(record_["confidence"], S.LOW)
        self.assertIn(conf_mod.DATA_QUALITY_WARNING, record_["confidence_reasons"])

    def test_authored_confidence_is_refused_whether_higher_or_lower(self):
        for level in (S.HIGH, S.LOW, S.MEDIUM):
            with self.assertRaises(strategy.StrategyError) as caught:
                strategy.build(self.synthesis,
                               [proposal([self.parts["demand"]], confidence=level)])
            self.assertIn("confidence", str(caught.exception))

    def test_the_derived_level_survives_into_the_claim(self):
        result = strategy.build(self.synthesis, [proposal([self.parts["demand"]],
                                                          action="Assess reported demand.")])
        self.assertEqual(result.claims()[0].confidence, S.MEDIUM)


class ConflictedEvidence(unittest.TestCase):
    """G — a conflict is carried whole and forces LOW; nothing is settled."""

    @classmethod
    def setUpClass(cls):
        ids = [item.id for item in close_market()["evidence_set"].items]
        declared = [{"subject": "UK chilled storage demand direction",
                     "positions": [{"evidence_id": ids[0], "value": 4, "unit": "%",
                                    "definition": "capacity demand growth"},
                                   {"evidence_id": ids[1], "value": -2, "unit": "%",
                                    "definition": "capacity demand growth"}]}]
        cls.synthesis = strict_set()
        cls.demand, cls.price, _capacity = add_external(
            cls.synthesis, retrieval=close_market(conflicts=declared))
        cls.result = strategy.build(cls.synthesis, [proposal(
            [cls.demand], action="Assess storage capacity against reported UK demand.")])
        cls.record = cls.result.recommendations[0]

    def test_the_recommendation_is_allowed_and_low(self):
        self.assertEqual(self.record["confidence"], S.LOW)
        self.assertIn(conf_mod.UNRESOLVED_CONFLICT, self.record["confidence_reasons"])

    def test_the_full_conflict_record_is_carried(self):
        self.assertTrue(self.record["conflicts"])
        conflict = self.record["conflicts"][0]
        self.assertTrue(conflict["unresolved"])
        self.assertEqual(len(conflict["positions"]), 2)
        self.assertNotIn("resolution", conflict)
        self.assertIn(conflict["conflict_id"], self.record["evidence_detail"][0]["conflict_refs"])

    def test_the_result_carries_the_set_conflicts_and_limitation(self):
        output = self.result.as_dict()
        self.assertEqual([c["conflict_id"] for c in output["conflicts"]],
                         [c.id for c in self.synthesis.conflicts])
        self.assertIn(lim_mod.UNRESOLVED_CONFLICT, [l["code"] for l in output["limitations"]])
        self.assertIn("**Conflicts**", strategy.render(self.result))


class PartialIncomparableAndUnresolved(unittest.TestCase):
    """H, I — weaker evidence is allowed and its reasons and limitations travel with it."""

    def test_partial_support_is_carried(self):
        synthesis, parts = mixed_set()
        record_ = strategy.build(synthesis, [proposal(
            [parts["demand"]], action="Assess reported demand.")]).recommendations[0]
        self.assertEqual(record_["support"], S.PARTIALLY_SUPPORTED)
        self.assertEqual(record_["evidence_detail"][0]["support"], S.PARTIALLY_SUPPORTED)
        self.assertIn(conf_mod.TIER_C_ONLY, record_["confidence_reasons"])

    def test_incomparable_values_carry_their_reason_and_limitation(self):
        joined = join(internal_dimensions=dict(INTERNAL_DIMENSIONS, geography="United Kingdom"))
        self.assertFalse(joined.compatible)
        record_ = strategy.build(joined.synthesis, [proposal(
            [joined.internal, joined.external],
            action="Review revenue reporting before relating it to the sector benchmark.",
            rationale="The internal revenue and the benchmark describe different territories.")
        ]).recommendations[0]
        self.assertIn(conf_mod.INCOMPARABLE_VALUES, record_["confidence_reasons"])
        self.assertEqual(record_["confidence"], S.LOW)
        output = strategy.build(joined.synthesis, []).as_dict()
        self.assertIn(lim_mod.INCOMPARABLE, [l["code"] for l in output["limitations"]])

    def test_unresolved_dimensions_are_reported_per_evidence_statement(self):
        joined = join(stated=claims(geography_excerpt="covers European operations"))
        self.assertIsNone(joined.external.dimensions["geography"])
        record_ = strategy.build(joined.synthesis, [proposal(
            [joined.external], action="Treat the sector benchmark as indicative only.",
            rationale="Its territory is not established by the source.")]).recommendations[0]
        detail = record_["evidence_detail"][0]
        self.assertIn("geography", detail["unresolved_dimensions"])
        self.assertTrue(detail["unresolved_dimensions"]["geography"])

    def test_statement_limitations_travel_with_the_recommendation(self):
        synthesis, parts = mixed_set()
        record_ = strategy.build(synthesis, [proposal([parts["margin"]])]).recommendations[0]
        self.assertEqual(record_["limitations"],
                         lim_mod.as_dicts(lim_mod.merge(parts["margin"].limitations)))
        self.assertTrue(record_["limitations"])
        self.assertEqual(record_["caveats"], parts["margin"].caveats)


class Materiality(unittest.TestCase):
    """J — inherited from the evidence, never re-judged."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()

    def test_material_evidence_marks_the_recommendation_material(self):
        record_ = strategy.build(self.synthesis,
                                 [proposal([self.parts["margin"]])]).recommendations[0]
        self.assertTrue(record_["material"])
        self.assertEqual(record_["evidence_detail"][0]["materiality"],
                         self.parts["margin"].as_dict()["materiality"])

    def test_non_material_evidence_is_allowed_and_marked(self):
        record_ = strategy.build(self.synthesis, [proposal(
            [self.parts["growth"]], action="Review capacity for continued growth.")]
        ).recommendations[0]
        self.assertFalse(self.parts["growth"].is_material)
        self.assertFalse(record_["material"])

    def test_mixed_materiality_is_material_and_visible_per_statement(self):
        record_ = strategy.build(self.synthesis, [proposal(
            [self.parts["growth"], self.parts["margin"]])]).recommendations[0]
        self.assertTrue(record_["material"])
        self.assertEqual([d["material"] for d in record_["evidence_detail"]],
                         [False, True])

    def test_material_statements_not_cited_are_listed(self):
        output = strategy.build(self.synthesis, [proposal([self.parts["margin"]])]).as_dict()
        material = [item.id for item in self.synthesis.material()
                    if item.id != self.parts["margin"].id]
        self.assertEqual(output["material_not_cited"], material)


class BusinessContextFraming(unittest.TestCase):
    """K — context frames the result and is never evidence."""

    @classmethod
    def setUpClass(cls):
        with io.open(DEMO_CONTEXT, encoding="utf-8") as handle:
            cls.context = context_mod.resolve(overrides=json.load(handle), load_files=False)
        cls.name = cls.context.get("identity.business_name")
        cls.synthesis, cls.parts = mixed_set(
            subject=cls.name, business_model=cls.context.get("identity.business_model"),
            currency=cls.context.get("reporting.currency"))
        cls.result = strategy.build(cls.synthesis, [proposal([cls.parts["margin"]])])

    def test_context_frames_the_heading(self):
        output = self.result.as_dict()
        self.assertEqual(output["subject"], self.name)
        self.assertEqual(output["business_model"], "retail")
        self.assertTrue(strategy.render(self.result).startswith(
            "# Strategy analysis — %s" % self.name))

    def test_context_cannot_be_cited_or_introduce_a_figure(self):
        for reference in ("identity.business_name", "business_context", self.name):
            with self.assertRaises(strategy.StrategyError):
                strategy.build(self.synthesis, [proposal([reference])])
        threshold = str(self.context.get("analysis.materiality.absolute_amount"))
        with self.assertRaises(strategy.StrategyError):
            strategy.build(self.synthesis, [proposal(
                [self.parts["margin"]],
                rationale="Movements above %s are material for this business." % threshold)])

    def test_the_private_name_is_not_evidence_and_never_reaches_a_query(self):
        detail = json.dumps(self.result.recommendations[0]["evidence_detail"])
        self.assertNotIn(self.name, detail)
        self.assertNotIn(self.name, json.dumps(open_market_brief()))


class ExpectedBenefit(unittest.TestCase):
    """L, M — qualitative, or a figure a cited statement already prints."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()

    def test_qualitative_benefit_is_accepted(self):
        record_ = strategy.build(self.synthesis, [proposal(
            [self.parts["margin"]],
            expected_benefit="A clearer, evidence-based view of where margin was lost.")]
        ).recommendations[0]
        self.assertEqual(record_["expected_benefit"],
                         "A clearer, evidence-based view of where margin was lost.")

    def test_a_figure_the_evidence_prints_is_accepted(self):
        record_ = strategy.build(self.synthesis, [proposal(
            [self.parts["margin"]],
            expected_benefit="Understanding what held average gross margin at 37.26% "
                             "earlier in the period.")]).recommendations[0]
        self.assertIn("37.26%", record_["expected_benefit"])

    def test_a_figure_the_evidence_does_not_print_is_refused(self):
        for benefit in ("Restores average gross margin to 38%.",
                        "Recovers USD 250000 of gross profit.",
                        "Improves margin by 2.9pp."):
            with self.assertRaises(strategy.StrategyError):
                strategy.build(self.synthesis,
                               [proposal([self.parts["margin"]], expected_benefit=benefit)])


class CommandLevelFlow(unittest.TestCase):
    """N — `/strategy-analysis` end to end, from the real runner and a real reply. No SWOT."""

    @classmethod
    def setUpClass(cls):
        cls.brief = open_market_brief()
        cls.command_run = C.run("business-health", source=DEMO)
        cls.joined = join()
        cls.synthesis = cls.joined.synthesis
        add_internal(cls.synthesis, run=cls.command_run, domains=("sales", "product"))
        cls.demand, cls.price, cls.capacity = add_external(cls.synthesis)
        legacy = find(cls.synthesis, LEGACY_DECLINE, S.ORIGIN_PRODUCT)
        cls.reading = S.interpretation(
            cls.synthesis, S.ORIGIN_PRODUCT,
            "The Legacy Crates line declined while a competing operator introduced a "
            "lower-priced chilled storage service.", supports=[legacy.id, cls.price.id])
        cls.assumed = S.assumption(cls.synthesis, S.ORIGIN_PRODUCT,
                                   "Customers are assumed to accept a narrower crate range.",
                                   "No customer preference data exists in the file.")
        cls.candidates = strategy.candidates(cls.synthesis)
        cls.result = strategy.build(cls.synthesis, [
            proposal([cls.reading],
                     action="Review whether the Legacy Crates line still fits the range.",
                     rationale="The line declined while a lower-priced competing service "
                               "arrived.",
                     expected_benefit="A range decision grounded in the line's own trend.",
                     risks=["Some customers may still depend on the line.",
                            "The competitor report is a single tier C source."],
                     dependencies=[{"text": "Customers accept a narrower range.",
                                    "assumption_id": cls.assumed.id}]),
            proposal([cls.capacity, cls.joined.external],
                     action="Assess chilled pallet capacity against the 3,500 new positions "
                            "reported in 2025.",
                     rationale="New capacity is opening in the market the benchmark covers.",
                     expected_benefit="A capacity view that reflects the 3.5k positions "
                                      "reported.",
                     risks=["Capacity figures describe the market, not this business."]),
        ])
        cls.output = cls.result.as_dict()
        cls.rendered = strategy.render(cls.result)

    def test_the_path_used_the_real_seams(self):
        self.assertEqual(self.brief["status"], R.AUTHORISED)
        self.assertIs(type(self.command_run), C.CommandResult)
        self.assertIs(type(self.joined), C.LocalJoin)
        self.assertTrue(self.joined.compatible)
        self.assertTrue(self.synthesis.require_dimension_provenance)

    def test_candidates_classify_every_statement(self):
        roles = dict((c["synthesis_id"], c["role"]) for c in self.candidates)
        self.assertEqual(roles[self.assumed.id], "assumption")
        self.assertEqual(roles[self.reading.id], "evidence")
        self.assertEqual(len(self.candidates), len(self.synthesis.items))

    def test_two_recommendations_are_issued_and_schema_valid(self):
        self.assertEqual(len(self.output["recommendations"]), 2)
        self.assertEqual(schema_errors(self.output), [])

    def test_the_first_recommendation_is_low_through_its_assumption(self):
        records = dict((r["action"], r) for r in self.output["recommendations"])
        legacy = records["Review whether the Legacy Crates line still fits the range."]
        self.assertEqual(legacy["confidence"], S.LOW)
        self.assertEqual(legacy["assumptions"][0]["synthesis_id"], self.assumed.id)

    def test_quoted_figures_in_differing_notation_are_grounded(self):
        records = [r for r in self.output["recommendations"] if "3,500" in r["action"]]
        self.assertEqual(len(records), 1)
        self.assertIn("3.5k", records[0]["expected_benefit"])

    def test_the_rendered_output_carries_the_contract(self):
        for token in ("# Strategy analysis", strategy.HUMAN_DECISION, strategy.ORDER_NOTE,
                      "**Action:**", "**Evidence**", "**Rationale:**", "**Expected benefit:**",
                      "**Risks**", "**Dependencies**", "**Confidence:**"):
            self.assertIn(token, self.rendered)

    def test_claims_validate_against_the_ledger_schema(self):
        ledger = evidence_mod.Ledger()
        self.result.record_in(ledger)
        document = {"schema_version": "1.0.0",
                    "claims": [c.as_dict() for c in ledger.claims]}
        self.assertEqual(schema_errors(document, LEDGER_SCHEMA), [])

    def test_no_swot_was_needed_and_nothing_internal_reached_the_query(self):
        sentinel = str(self.joined.internal.observed)
        self.assertNotIn(sentinel, json.dumps(self.brief))
        self.assertNotIn(sentinel.split(".")[0], self.brief["brief"]["query_text"])
        self.assertNotIn("swot", code(STRATEGY_PY).lower())


# =======================================================================================
# B. Negative / fail-closed
# =======================================================================================

class FailClosed(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()

    def refused(self, proposals, synthesis=None, contains=None):
        with self.assertRaises(strategy.StrategyError) as caught:
            strategy.build(self.synthesis if synthesis is None else synthesis, proposals)
        if contains:
            self.assertIn(contains, str(caught.exception))
        return caught.exception

    # -- evidence ------------------------------------------------------------

    def test_a_fake_evidence_id_is_refused(self):
        self.refused([proposal(["sy-000000000000"])],
                     contains="not a statement in this synthesis set")

    def test_an_out_of_set_evidence_id_is_refused(self):
        other = strict_set()
        demand, _price, _capacity = add_external(other)
        internal_only = add_internal(strict_set(), domains=("financial",))
        self.refused([proposal([demand.id])], synthesis=internal_only,
                     contains="not a statement in this synthesis set")

    def test_an_ambiguous_evidence_id_is_refused(self):
        synthesis = strict_set()
        for _ in range(2):
            C.internal_statements(synthesis, shared_run(), S.ORIGIN_FINANCIAL, DATASET_ID,
                                  domains=["financial"])
        margin = [i for i in synthesis.items if i.statement.startswith(MARGIN_DECLINE)][0]
        self.refused([proposal([margin])], synthesis=synthesis,
                     contains="identifies 2 statements")

    def test_empty_missing_non_list_or_duplicated_evidence_is_refused(self):
        margin = self.parts["margin"].id
        for evidence in ([], "", None, margin, [margin, margin], [42], [None]):
            record_ = proposal([self.parts["margin"]])
            record_["evidence"] = evidence
            self.refused([record_])

    def test_evidence_that_is_only_an_assumption_is_refused(self):
        self.refused([proposal([self.parts["assumed"]])],
                     contains="An assumption is never evidence")

    def test_evidence_naming_a_recommendation_is_refused(self):
        issued = strategy.build(self.synthesis, [proposal([self.parts["margin"]])])
        rec_id = issued.recommendations[0]["recommendation_id"]
        self.refused([proposal([rec_id])], contains="not a statement in this synthesis set")
        self.refused([proposal([self.parts["margin"], rec_id])])

    def test_a_smuggled_recommendation_statement_is_not_evidence(self):
        synthesis = add_internal(strict_set(), domains=("financial",))
        smuggled = find(synthesis, MARGIN_DECLINE)
        smuggled.kind = S.RECOMMENDATION
        self.refused([proposal([smuggled])], synthesis=synthesis, contains="not evidence")

    def test_evidence_graded_unsupported_is_refused(self):
        synthesis = strict_set()
        demand, _price, _capacity = add_external(
            synthesis, materiality={"outcome": "material", "reason": "fixture"})
        self.assertEqual(demand.support, S.UNSUPPORTED)
        self.refused([proposal([demand], action="Assess reported demand.")],
                     synthesis=synthesis, contains="graded statement")

    def test_evidence_graded_insufficient_is_refused(self):
        synthesis = add_internal(strict_set(), domains=("financial",))
        opinion = synthesis.add(sc.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_FINANCIAL, "The brand is widely admired.",
            provenance=[sc.ProvenanceRef.unavailable("nothing was measured")]))
        self.assertEqual(opinion.support, S.INSUFFICIENT_EVIDENCE)
        self.refused([proposal([opinion])], synthesis=synthesis)

    def test_an_interpretation_with_invalid_supports_is_refused(self):
        synthesis = add_internal(strict_set(), domains=("financial",))
        margin = find(synthesis, MARGIN_DECLINE)
        bare = synthesis.add(sc.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_FINANCIAL, "The margin picture is mixed.",
            provenance=[sc.ProvenanceRef(sc.P_DATASET, DATASET_ID)]))
        self.refused([proposal([bare])], synthesis=synthesis,
                     contains="names no supporting statements")
        assumed = S.assumption(synthesis, S.ORIGIN_FINANCIAL, "Costs stay flat.",
                               "No cost forecast exists.")
        leaning = S.interpretation(synthesis, S.ORIGIN_FINANCIAL,
                                   "Margin pressure is unlikely to ease on its own.",
                                   supports=[margin.id, assumed.id])
        self.refused([proposal([leaning])], synthesis=synthesis,
                     contains="assumption is not evidence")

    def test_circular_support_is_refused(self):
        synthesis = add_internal(strict_set(), domains=("financial",))
        margin = find(synthesis, MARGIN_DECLINE)
        text = "Margin weakness supports itself."
        own = sc.synthesis_id(S.INTERPRETATION, S.ORIGIN_FINANCIAL, text)
        circular = synthesis.add(sc.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_FINANCIAL, text, provenance=list(margin.provenance),
            notes=["%s%s" % (merge_mod.RESTS_ON, own)]))
        self.refused([proposal([circular])], synthesis=synthesis, contains="circular")

    # -- authored fields -----------------------------------------------------

    def test_caller_forged_provenance_and_conclusions_are_refused(self):
        for field, value in (("provenance", [{"kind": "dataset", "ref_id": DATASET_ID}]),
                             ("support", S.SUPPORTED), ("trust", "internal"),
                             ("verified", True), ("source_tier", "A"),
                             ("evidence_detail", []), ("recommendation_id", "rec-000000000000"),
                             ("issued_by", "someone"), ("based_on", ["x"]),
                             ("confidence", S.HIGH)):
            self.refused([proposal([self.parts["margin"]], **{field: value})],
                         contains="is not accepted")

    def test_priority_score_rank_weight_and_estimates_are_refused(self):
        for field in ("priority", "score", "rank", "weight", "top", "winner",
                      "estimated_value", "execution_status", "decision_owner"):
            self.refused([proposal([self.parts["margin"]], **{field: 1})], contains=field)

    def test_each_empty_authored_field_is_refused(self):
        for field, empty in (("action", ""), ("action", "   "), ("rationale", ""),
                             ("expected_benefit", " "), ("risks", []), ("risks", [""]),
                             ("risks", "a risk"), ("dependencies", []),
                             ("dependencies", [{"text": ""}]),
                             ("dependencies", "a dependency")):
            self.refused([proposal([self.parts["margin"]], **{field: empty})])

    def test_a_missing_authored_field_is_refused(self):
        for field in strategy.AUTHORED_FIELDS:
            record_ = proposal([self.parts["margin"]])
            del record_[field]
            self.refused([record_])

    def test_singular_and_alias_fields_are_refused(self):
        for alias in ("risk", "dependency", "benefit", "statement"):
            record_ = proposal([self.parts["margin"]])
            record_[alias] = "x"
            self.refused([record_], contains=alias)

    def test_an_invalid_assumption_reference_is_refused(self):
        for assumption_id, contains in (("sy-000000000000", "not a statement"),
                                        (self.parts["margin"].id, "not an assumption")):
            self.refused([proposal([self.parts["margin"]], dependencies=[
                {"text": "Something assumed.", "assumption_id": assumption_id}])],
                contains=contains)
        self.refused([proposal([self.parts["margin"]], dependencies=[
            {"text": "Something assumed.", "assumption_id": 7}])])
        self.refused([proposal([self.parts["margin"]], dependencies=[
            {"text": "Something assumed.", "owner": "finance"}])], contains="owner")

    def test_proposals_must_be_a_list_of_records(self):
        for value in ({"action": "x"}, "x", None, 3):
            self.refused(value)
        self.refused(["a recommendation"])

    # -- the input object ----------------------------------------------------

    def test_a_non_strict_set_is_refused(self):
        loose = add_internal(S.SynthesisSet(subject="loose"), domains=("financial",))
        self.refused([proposal([find(loose, MARGIN_DECLINE)])], synthesis=loose,
                     contains="require_dimension_provenance=True")

    def test_a_serialised_or_look_alike_set_is_refused(self):
        class LookAlike(object):
            require_dimension_provenance = True
            items = self.synthesis.items

        class Subclass(S.SynthesisSet):
            pass

        for fake in (self.synthesis.as_dict(), self.synthesis.to_json(),
                     S.load(json.loads(self.synthesis.to_json())), LookAlike(),
                     Subclass(require_dimension_provenance=True), None):
            with self.assertRaises(strategy.StrategyError):
                strategy.build(fake, [proposal([self.parts["margin"]])])
            with self.assertRaises(strategy.StrategyError):
                strategy.candidates(fake)

    def test_an_empty_or_ungraded_set_is_refused(self):
        self.refused([], synthesis=strict_set(), contains="holds no statements")
        synthesis = add_internal(strict_set(), domains=("financial",))
        margin = find(synthesis, MARGIN_DECLINE)
        synthesis._items.append(sc.SynthesisItem(
            S.CALCULATION, S.ORIGIN_FINANCIAL, "Gross margin is 99.00%.",
            provenance=list(margin.provenance), basis="gross_margin"))
        self.refused([proposal([margin])], synthesis=synthesis, contains="never graded")

    def test_a_result_cannot_be_assembled_outside_build(self):
        with self.assertRaises(strategy.StrategyError):
            strategy.StrategyResult(self.synthesis, [proposal([self.parts["margin"]])],
                                    "sha256:" + "0" * 64)

    def test_a_result_refuses_to_speak_for_a_set_that_changed(self):
        synthesis, parts = mixed_set()
        result = strategy.build(synthesis, [proposal([parts["margin"]])])
        S.assumption(synthesis, S.ORIGIN_FINANCIAL, "A later assumption.", "Added afterwards.")
        self.assertFalse(result.is_bound_to(synthesis))
        with self.assertRaises(strategy.StrategyError):
            result.claims()
        with self.assertRaises(strategy.StrategyError):
            result.as_dict()

    def test_editing_a_returned_record_changes_nothing(self):
        result = strategy.build(self.synthesis, [proposal([self.parts["margin"]])])
        copy_ = result.recommendations[0]
        copy_["confidence"] = "HIGH"
        copy_["evidence"].append("sy-000000000000")
        self.assertEqual(result.recommendations[0]["evidence"], [self.parts["margin"].id])


class ClassSevenClaimShape(unittest.TestCase):
    """The ledger refuses a class-7 claim whose fields are placeholders (ADR-0031)."""

    def valid(self, **overrides):
        fields = dict(evidence=["sy-0123456789ab"], rationale="r", expected_benefit="b",
                      risks=["k"], dependencies=[{"text": "d", "assumption_id": None}],
                      confidence="LOW")
        fields.update(overrides)
        return fields

    def test_the_canonical_shape_constructs(self):
        claim = evidence_mod.Claim("Do x.", evidence_mod.RECOMMENDATION, **self.valid())
        self.assertEqual(claim.based_on, ["sy-0123456789ab"])

    def test_placeholders_and_wrong_shapes_are_refused(self):
        for field, value in (("evidence", "e"), ("evidence", []), ("evidence", ["prose"]),
                             ("evidence", ["sy-0123456789ab", "sy-0123456789ab"]),
                             ("risks", "k"), ("risks", [""]), ("dependencies", "d"),
                             ("dependencies", [{"text": "d"}]),
                             ("dependencies", [{"text": "d", "assumption_id": "a"}]),
                             ("rationale", "  "), ("confidence", "VERY HIGH")):
            with self.assertRaises(evidence_mod.LedgerError, msg=field):
                evidence_mod.Claim("Do x.", evidence_mod.RECOMMENDATION,
                                   **self.valid(**{field: value}))

    def test_text_based_on_and_extra_fields_are_refused(self):
        with self.assertRaises(evidence_mod.LedgerError):
            evidence_mod.Claim("Do x.", evidence_mod.RECOMMENDATION,
                               based_on=["Revenue was 5."], **self.valid())
        for extra in ("priority", "risk", "action"):
            with self.assertRaises(evidence_mod.LedgerError):
                evidence_mod.Claim("Do x.", evidence_mod.RECOMMENDATION,
                                   **self.valid(**{extra: "x"}))
        with self.assertRaises(evidence_mod.LedgerError):
            evidence_mod.Claim("  ", evidence_mod.RECOMMENDATION, **self.valid())

    def test_the_id_spelling_matches_the_synthesis_id_function(self):
        generated = sc.synthesis_id(S.CALCULATION, S.ORIGIN_SALES, "any statement")
        self.assertTrue(evidence_mod.RECOMMENDATION_EVIDENCE_ID.match(generated))

    def test_the_ledger_schema_enforces_class_seven(self):
        base = evidence_mod.Claim("Do x.", evidence_mod.RECOMMENDATION,
                                  **self.valid()).as_dict()
        document = lambda claim: {"schema_version": "1.0.0", "claims": [claim]}  # noqa: E731
        self.assertEqual(schema_errors(document(base), LEDGER_SCHEMA), [])
        for mutate in (lambda c: c.pop("rationale"), lambda c: c.update(risks=[]),
                       lambda c: c.update(evidence=["e"]), lambda c: c.update(risk="k"),
                       lambda c: c.update(priority=1), lambda c: c.update(confidence=None),
                       lambda c: c["dependencies"][0].update(owner="x")):
            claim = json.loads(json.dumps(base))
            mutate(claim)
            self.assertTrue(schema_errors(document(claim), LEDGER_SCHEMA), claim)

    def test_other_classes_are_unaffected(self):
        self.assertTrue(evidence_mod.Claim("x", evidence_mod.INTERPRETATION))
        sourced = evidence_mod.Claim("A source said x.", evidence_mod.EXTERNAL_SOURCED,
                                     source="S", citation="c", source_date="2026-01-01",
                                     source_tier="B").as_dict()
        self.assertEqual(schema_errors({"schema_version": "1.0.0", "claims": [sourced]},
                                       LEDGER_SCHEMA), [])


# =======================================================================================
# C. Number rule
# =======================================================================================

class FigureTokens(unittest.TestCase):

    def tokens(self, text):
        return strategy.figure_tokens(text)

    def figure(self, kind, value, currency=None):
        return ("figure", (kind, Decimal(value).normalize(), currency))

    def test_plain_grouped_and_scaled_forms_are_the_same_value(self):
        for text in ("3500", "3,500", "3.5k", "3.5 thousand"):
            self.assertEqual(self.tokens(text), [self.figure(strategy.AMOUNT, "3500")], text)
        self.assertEqual(self.tokens("USD 3.47 million"),
                         [self.figure(strategy.AMOUNT, "3470000", "USD")])

    def test_percent_and_percentage_points_are_distinct_kinds(self):
        self.assertEqual(self.tokens("35%")[0], self.figure(strategy.PERCENT, "35"))
        self.assertEqual(self.tokens("35 percent")[0], self.figure(strategy.PERCENT, "35"))
        self.assertEqual(self.tokens("-2.85pp")[0],
                         self.figure(strategy.PERCENTAGE_POINTS, "-2.85"))

    def test_currency_markers(self):
        self.assertEqual(self.tokens("USD 5")[0], self.figure(strategy.AMOUNT, "5", "USD"))
        self.assertEqual(self.tokens("5 USD")[0], self.figure(strategy.AMOUNT, "5", "USD"))
        self.assertEqual(self.tokens("£5m")[0], self.figure(strategy.AMOUNT, "5000000", "GBP"))
        self.assertEqual(self.tokens("$5")[0], self.figure(strategy.AMOUNT, "5", "$"))
        with self.assertRaises(strategy.StrategyError):
            self.tokens("EUR 5 USD")

    def test_dates_are_not_figures(self):
        self.assertEqual(self.tokens("in 2025, from 2024-01 to 2026-09-16"),
                         [("date", "2025"), ("date", "2024-01"), ("date", "2026-09-16")])
        self.assertEqual(self.tokens("USD 2025")[0][0], "figure")
        self.assertEqual(self.tokens("2025%")[0][0], "figure")
        self.assertEqual(self.tokens("2204 rows")[0][0], "figure")

    def test_identifiers_are_not_figures(self):
        for word in ("Q3", "FY2026", "v2.1.3", "46-390", "sy-7cf1c90f8c67", "1,2345"):
            self.assertEqual(self.tokens("see %s here" % word), [("identifier", word)], word)

    def test_a_non_ascii_numeral_is_refused(self):
        with self.assertRaises(strategy.StrategyError):
            self.tokens("growth of ٣٥%")

    def test_no_digits_means_no_tokens(self):
        self.assertEqual(self.tokens("about half, roughly double, a few"), [])


class FigureGrounding(unittest.TestCase):

    EVIDENCE = ["Revenue is USD 3467850.16.",
                "Average gross margin moved from 37.26% to 34.41%, a change of -2.85pp.",
                "A capacity watch reports 3,500 new chilled pallet positions opened in 2025.",
                "Revenue is recorded across 24 months, from 2024-01 to 2025-12."]

    def ok(self, text, evidence=None, ids=()):
        strategy.require_grounded("rationale", text,
                                  self.EVIDENCE if evidence is None else evidence, ids)

    def refused(self, text, evidence=None, ids=()):
        with self.assertRaises(strategy.StrategyError, msg=text):
            self.ok(text, evidence, ids)

    def test_supported_forms_are_accepted(self):
        for text in ("Across 24 months.", "Revenue of USD 3467850.16.",
                     "Revenue of USD 3,467,850.16.", "Revenue of 3467850.16.",
                     "Some 3,500 positions.", "Some 3500 positions.", "Some 3.5k positions.",
                     "Margin reached 37.26%.", "A move of -2.85pp.", "From 2024-01.",
                     "During 2025.", "Qualitative only."):
            self.ok(text)

    def test_unsupported_and_near_figures_are_refused(self):
        for text in ("Across 25 months.", "Margin reached 37.3%.", "Margin reached 37%.",
                     "Revenue of USD 3.47 million.", "Some 3.6k positions.",
                     "A move of 2.85pp.", "Revenue of EUR 3467850.16.",
                     "Margin reached 37.26pp.", "From 2023-01.", "During 2027.",
                     "Roughly 4k positions."):
            self.refused(text)

    def test_a_percent_is_not_grounded_by_a_bare_number_or_the_reverse(self):
        self.refused("Margin reached 37.26.")
        self.refused("About 24% of months.")

    def test_a_year_cannot_ground_an_amount_or_an_amount_a_year(self):
        self.refused("USD 2025 of revenue.", ["Revenue grew in 2025."])
        self.refused("During 2025.", ["Revenue was USD 2025 in the pilot."])

    def test_identifiers_must_be_printed_or_cited(self):
        self.refused("Report it for FY2026.")
        self.ok("Report it for FY2026.", ["Targets are published for FY2026."])
        self.ok("See sy-0123456789ab.", ids=["sy-0123456789ab"])
        self.refused("See sy-0123456789ab.")

    def test_an_unmarked_figure_matching_two_currencies_is_ambiguous(self):
        evidence = ["Sales were USD 500 in one region.", "Sales were EUR 500 in another."]
        self.refused("Sales of 500.", evidence)
        self.ok("Sales of USD 500.", evidence)

    def test_ambiguous_dollar_symbol_never_matches_a_code(self):
        self.refused("Revenue of $3467850.16.")

    def test_only_cited_statements_ground_a_figure(self):
        synthesis, parts = mixed_set()
        with self.assertRaises(strategy.StrategyError):
            strategy.build(synthesis, [proposal(
                [parts["margin"]], rationale="Revenue growth of 69.72% hid the decline.")])
        result = strategy.build(synthesis, [proposal(
            [parts["margin"], parts["growth"]],
            rationale="Revenue growth of 69.72% hid the decline.")])
        self.assertEqual(len(result.recommendations), 1)

    def test_each_checked_field_is_checked(self):
        synthesis, parts = mixed_set()
        for field, value in (("action", "Cut prices by 5%."),
                             ("rationale", "Margin fell by 3pp."),
                             ("expected_benefit", "Saves USD 10000."),
                             ("risks", ["Volume may fall 10%."])):
            with self.assertRaises(strategy.StrategyError, msg=field):
                strategy.build(synthesis, [proposal([parts["margin"]], **{field: value})])

    def test_a_dependency_may_quote_its_own_assumption_but_the_action_may_not(self):
        synthesis, parts = mixed_set()
        assumed = S.assumption(synthesis, S.ORIGIN_FINANCIAL,
                               "Input costs are assumed to rise 3% next year.",
                               "No cost forecast exists.")
        strategy.build(synthesis, [proposal([parts["margin"]], dependencies=[
            {"text": "Input costs rise no more than 3%.", "assumption_id": assumed.id}])])
        with self.assertRaises(strategy.StrategyError):
            strategy.build(synthesis, [proposal(
                [parts["margin"]], action="Plan for input costs rising 3%.",
                dependencies=[{"text": "Input costs rise as assumed.",
                               "assumption_id": assumed.id}])])


# =======================================================================================
# D. Traceability, the single grounding home, and anti-re-entry
# =======================================================================================

class Traceability(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.result = strategy.build(cls.synthesis, [
            proposal([cls.parts["margin"]]),
            proposal([cls.parts["growth"], cls.parts["demand"]],
                     action="Assess capacity against growth and reported demand.")])

    def test_every_evidence_id_is_a_statement_in_the_set(self):
        held = dict((item.id, item) for item in self.synthesis.items)
        for record_ in self.result.recommendations:
            for detail in record_["evidence_detail"]:
                item = held[detail["synthesis_id"]]
                self.assertEqual(detail["statement"], item.statement)
                self.assertEqual(detail["kind"], item.kind)
                self.assertEqual(detail["origin"], item.origin)
                self.assertEqual(detail["confidence"], item.confidence)

    def test_statement_text_is_not_accepted_as_evidence(self):
        with self.assertRaises(strategy.StrategyError):
            strategy.build(self.synthesis, [proposal([self.parts["margin"].statement])])

    def test_claims_carry_ids_not_text(self):
        for claim, record_ in zip(self.result.claims(), self.result.recommendations):
            self.assertEqual(claim.based_on, record_["evidence"])
            self.assertEqual(claim.extra["evidence"], record_["evidence"])
            self.assertTrue(all(e.startswith("sy-") for e in claim.based_on))

    def test_mixed_provenance_stays_separate(self):
        record_ = [r for r in self.result.recommendations if len(r["evidence"]) == 2][0]
        chains = dict((d["synthesis_id"], d["chain"]) for d in record_["evidence_detail"])
        internal_kinds = {e["kind"] for e in chains[self.parts["growth"].id]}
        external_kinds = {e["kind"] for e in chains[self.parts["demand"].id]}
        self.assertNotIn("evidence", internal_kinds)
        self.assertEqual(external_kinds, {"evidence"})


class SingleGroundingHome(unittest.TestCase):
    """ADR-0031: SWOT and Strategy share one implementation of the ADR-0030 checks."""

    def test_only_grounding_reads_the_supports_note(self):
        readers = []
        for root, _dirs, files in os.walk(LIB):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    if "interpretation_supports(" in code(path) and path != MERGE_PY:
                        readers.append(os.path.relpath(path, LIB))
        self.assertEqual(sorted(readers), [os.path.join("synthesis", "grounding.py")])
        for consumer in (STRATEGY_PY, SWOT_PY):
            self.assertIn("grounding.interpretation_supports", code(consumer))
            self.assertNotIn("merge_mod", code(consumer))

    def test_there_is_exactly_one_definition_of_each_check(self):
        definitions = {}
        for root, _dirs, files in os.walk(LIB):
            for name in files:
                if name.endswith(".py"):
                    body = code(os.path.join(root, name))
                    for check in ("def genuine_set", "def interpretation_domains",
                                  "def evidence_domains", "def _rests_on", "def graded",
                                  "def _graded"):
                        definitions.setdefault(check, 0)
                        definitions[check] += len(re.findall(r"^%s\b" % check, body, re.M))
        self.assertEqual(definitions["def genuine_set"], 1)
        self.assertEqual(definitions["def interpretation_domains"], 1)
        self.assertEqual(definitions["def evidence_domains"], 1)
        self.assertEqual(definitions["def graded"], 1)
        self.assertEqual(definitions["def _rests_on"], 0)
        self.assertEqual(definitions["def _graded"], 0)

    def test_the_shared_module_knows_no_consumer(self):
        body = code(GROUNDING_PY).lower()
        for name in ("swot", "strategy", "quadrant"):
            self.assertNotIn(name, body)

    def test_swot_and_strategy_refuse_the_same_forged_interpretation(self):
        synthesis = add_internal(strict_set(), domains=("financial", "product"))
        margin = find(synthesis, MARGIN_DECLINE)
        legacy = find(synthesis, LEGACY_DECLINE, S.ORIGIN_PRODUCT)
        forged = synthesis.add(sc.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_FINANCIAL, "Margin weakness is broad-based.",
            provenance=list(legacy.provenance),
            notes=["%s%s" % (merge_mod.RESTS_ON, margin.id)]))
        with self.assertRaises(swot.SwotError) as swot_refusal:
            swot.build(synthesis, [{"quadrant": swot.WEAKNESSES,
                                    "tag": swot.ANALYTICAL_INFERENCE,
                                    "synthesis_id": forged.id}])
        with self.assertRaises(strategy.StrategyError) as strategy_refusal:
            strategy.build(synthesis, [proposal([forged])])
        self.assertEqual(str(swot_refusal.exception), str(strategy_refusal.exception))


class AntiReentry(unittest.TestCase):
    """Recommendations never re-enter synthesis, in any form (ADR-0031 constraint 6)."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.result = strategy.build(cls.synthesis, [proposal([cls.parts["margin"]])])
        cls.serialised = cls.result.as_dict()["recommendations"][0]

    def test_a_recommendation_cannot_be_a_synthesis_item(self):
        with self.assertRaises(sc.SynthesisError):
            sc.SynthesisItem(S.RECOMMENDATION, S.ORIGIN_FINANCIAL, self.serialised["action"],
                             provenance=[sc.ProvenanceRef(sc.P_DATASET, DATASET_ID)])

    def test_the_synthesis_recommendations_collection_stays_empty(self):
        self.assertEqual(self.synthesis.recommendations, [])
        with self.assertRaises(AttributeError):
            self.synthesis.recommendations = [self.serialised]
        self.synthesis.recommendations.append(self.serialised)
        self.assertEqual(self.synthesis.recommendations, [])
        schema = json.loads(read(SYNTHESIS_SCHEMA))
        self.assertEqual(schema["properties"]["recommendations"]["maxItems"], 0)

    def test_register_claims_refuses_every_spelling_of_a_recommendation(self):
        claim = self.result.claims()[0].as_dict()
        variants = [dict(self.serialised), claim,
                    dict(claim, label="SOURCED", **{"class": 3}),
                    {"statement": "x", "class": 7}, {"statement": "x", "class": "7"},
                    {"statement": "x", "label": "recommendation"},
                    {"statement": "x", "finding_type": "RECOMMENDATION"},
                    {"statement": "x", "kind": "RECOMMENDATION"},
                    {"statement": "x", "recommendation_id": "rec-000000000000"},
                    {"statement": "x", "action": "Do it."},
                    {"statement": "x", "expected_benefit": "More."},
                    {"statement": "x", "issued_by": strategy.ISSUED_BY}]
        for variant in variants:
            synthesis = strict_set()
            with self.assertRaises(sc.SynthesisError, msg=variant):
                synthesis.register_claims([variant])
            self.assertEqual(synthesis.candidate_claims, [])

    def test_a_genuine_candidate_claim_is_still_accepted(self):
        synthesis = strict_set()
        registered = synthesis.register_claims([{"statement": "A source said x.",
                                                 "evidence_id": "ev-1", "class": 3,
                                                 "label": "SOURCED"}])
        self.assertEqual(len(registered), 1)

    def test_recommendation_wording_cannot_enter_upstream_as_a_reading(self):
        with self.assertRaises(sc.SynthesisError):
            S.interpretation(self.synthesis, S.ORIGIN_FINANCIAL,
                             "We recommend reviewing pricing on the declining lines.",
                             supports=[self.parts["margin"].id])
        with self.assertRaises(sc.SynthesisError):
            S.sourced_statement(self.synthesis, S.ORIGIN_MARKET,
                                "You should expand chilled capacity immediately.",
                                evidence_ids=[self.parts["demand"].provenance[0].ref_id])

    def test_the_engine_has_no_path_into_synthesis_authoring(self):
        body = code(STRATEGY_PY)
        for call in ("interpretation(", "sourced_statement(", "register_claims(",
                     "register_external(", "synthesis.add(", "assumption(",
                     "footed_statement(", "from_analysis_set(", "from_kpi_result(",
                     "local_join(", "add_conflict(", "limit(", "._items"):
            self.assertNotIn(call, body, call)
        # The only `.add(` calls are on a Python set and on an evidence ledger. M10.3.3 added the
        # `number_words` set for figures written in words.
        for line in body.splitlines():
            if ".add(" in line:
                self.assertTrue(re.search(r"\b(markers|dates|words|number_words|seen|ledger)\.add\(",
                                          line), line)

    def test_the_engine_cannot_reach_files_the_network_or_analysis(self):
        body = code(STRATEGY_PY)
        for token in ("open(", "urllib", "socket", "http", "subprocess", "open_retrieval",
                      "close_retrieval", "scout", "gate", "commands", "pipeline", "ingest"):
            self.assertNotIn(token, body, token)


# =======================================================================================
# E. Output: nothing ranked, scored or executed
# =======================================================================================

class Output(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.synthesis, cls.parts = mixed_set()
        cls.result = strategy.build(cls.synthesis, [
            proposal([cls.parts["margin"]]),
            proposal([cls.parts["demand"]], action="Assess reported demand.")])
        cls.output = cls.result.as_dict()

    def test_the_result_has_exactly_its_declared_fields(self):
        self.assertEqual(set(self.output), {
            "schema_version", "analysis", "issued_by", "subject", "as_of", "business_model",
            "currency", "quality_grade", "synthesis_digest", "trust_statement",
            "human_decision", "order_note", "recommendations", "empty_state",
            "material_not_cited", "conflicts", "limitations", "confidence"})

    def test_each_recommendation_has_the_contract_fields(self):
        for record_ in self.output["recommendations"]:
            for field in strategy.AUTHORED_FIELDS + ("confidence",):
                self.assertTrue(record_[field], field)
            self.assertIn(record_["confidence"], conf_mod.LEVELS)

    def test_no_rank_score_priority_weight_winner_or_execution_field_at_any_depth(self):
        forbidden = re.compile(r"rank|score|priorit|weight|winner|top_|best|estimated|"
                               r"execut|owner", re.I)
        self.assertEqual(sorted(k for k in all_keys(self.output) if forbidden.search(k)), [])
        self.assertFalse(strategy.EXECUTES_ACTIONS)

    def test_the_schema_is_closed_against_ranking_scores_and_execution(self):
        for path, extra in ((None, {"priority": 1}), (None, {"top_recommendation": "x"}),
                            (0, {"score": 9}), (0, {"rank": 1}), (0, {"weight": 0.5}),
                            (0, {"estimated_value": 100}), (0, {"execution_status": "done"}),
                            (0, {"decision_owner": "CEO"})):
            record_ = json.loads(json.dumps(self.output, default=str))
            (record_ if path is None else record_["recommendations"][path]).update(extra)
            self.assertTrue(schema_errors(record_), extra)

    def test_the_rendered_output_has_no_ranking_language_or_numbering(self):
        rendered = strategy.render(self.result)
        headings = [l for l in rendered.split("\n") if l.startswith("#")]
        self.assertEqual(headings[:2], ["# Strategy analysis — Northwind demo",
                                        "## Recommendations"])
        self.assertTrue(all(re.match(r"^### `rec-[0-9a-f]{12}`$", h) for h in headings[2:]))
        lowered = rendered.lower()
        for phrase in ("top recommendation", "highest priority", "priority:", "score",
                       "rank:", "winner", "best option", "executed", "status:"):
            self.assertNotIn(phrase, lowered, phrase)
        self.assertIn(strategy.HUMAN_DECISION, rendered)

    def test_an_empty_result_states_it(self):
        empty = strategy.build(self.synthesis, [])
        output = empty.as_dict()
        self.assertEqual(output["recommendations"], [])
        self.assertEqual(output["empty_state"], strategy.EMPTY_STATE)
        self.assertEqual(schema_errors(output), [])
        self.assertIn(strategy.EMPTY_STATE, strategy.render(empty))

    def test_serialisation_is_deterministic_across_independent_builds(self):
        first_set, first = mixed_set()
        second_set, second = mixed_set()
        a = strategy.build(first_set, [proposal([first["margin"]])]).to_json()
        b = strategy.build(second_set, [proposal([second["margin"]])]).to_json()
        self.assertEqual(a, b)


class SkillAndCommand(unittest.TestCase):

    def test_the_skill_is_discoverable_with_supported_frontmatter(self):
        block = frontmatter(read(SKILL_MD))
        self.assertTrue(re.search(r"^name:\s*bops-strategy-recommendations\s*$", block, re.M))
        declared = set(re.findall(r"^([a-zA-Z-]+):", block, re.M))
        self.assertTrue(declared <= {"name", "description", "argument-hint",
                                     "user-invocable"}, declared)

    def test_the_command_is_thin_and_names_the_skill(self):
        text = read(COMMAND_MD)
        declared = set(re.findall(r"^([a-zA-Z-]+):", frontmatter(text), re.M))
        self.assertTrue(declared <= {"description", "argument-hint", "allowed-tools",
                                     "disable-model-invocation",
                                     "hide-from-slash-command-tool"}, declared)
        self.assertIn("`bops-strategy-recommendations`", text)
        self.assertIn("This command sequences", text)
        self.assertIn("**None required to run.**", text)
        self.assertIn("A SWOT is not required.", text)

    def test_both_state_the_contract_and_the_action_boundary(self):
        skill = " ".join(read(SKILL_MD).split())
        for token in strategy.AUTHORED_FIELDS + ("strategy.build(", "strategy.candidates(",
                                                 "never counted as evidence",
                                                 "Figures are quoted, never produced",
                                                 "financial transactions are prohibited"):
            self.assertIn(token, skill, token)
        command = " ".join(read(COMMAND_MD).split()).lower()
        self.assertIn("nothing internal is sent as a fallback", command)
        self.assertIn("financial transactions are prohibited", command)

    def test_executive_report_is_built_and_issues_no_recommendations(self):
        """Amended by the Executive Report implementation: it ships, and it is not an issuer."""
        skills = set(os.listdir(os.path.join(REPO_ROOT, "skills")))
        commands = {n[:-3] for n in os.listdir(os.path.join(REPO_ROOT, "commands"))}
        self.assertIn("bops-executive-report", skills)
        self.assertIn("executive-report", commands)
        self.assertTrue(os.path.exists(os.path.join(LIB, "executive_report.py")))
        self.assertNotIn("bops-executive-report", strategy.RECOMMENDATION_ISSUERS)
        self.assertNotIn("executive", code(STRATEGY_PY).lower())


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
