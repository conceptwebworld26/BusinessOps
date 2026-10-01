"""A deterministic cross-domain synthesis fixture: internal, external, and the seams.

The point of this fixture is not volume. It is that one object contains every case the
synthesis layer has to keep apart - an internal calculation and an external quotation, a
material movement and an immaterial one, a forecast and an anomaly, a candidate claim that
stays candidate, a conflict that stays unresolved, and a limitation that survives being
combined with everything else.

**The external evidence here is synthetic.** Every reference points at `example.invalid`,
a reserved domain that can never resolve, and every source name is prefixed `DEMO`. A
fixture that carried a plausible-looking real citation would be a fabricated source in the
test suite, and the first time someone copied one into a report it would read as real.
Nothing here may be mistaken for a genuine external source, which also means every item
classifies locally as tier C - correctly, since an unrecognised domain earns nothing more.

Built at test time. No file on disk is modified and no network call is made.
"""

import os
import sys
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENGINE_PATH = os.path.join(REPO_ROOT, "lib", "python")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

from bops import materiality as materiality_mod            # noqa: E402
from bops import synthesis as synthesis_mod                # noqa: E402
from bops.analytics import contract as analytics_contract  # noqa: E402
from bops.research import evidence_set as evidence_mod     # noqa: E402
from bops.research import sources as sources_mod           # noqa: E402

#: Reserved by RFC 2606; guaranteed never to resolve. Demo citations live here so that a
#: fixture citation can never be mistaken for, or copied as, a real source.
DEMO_HOST = "https://research.example.invalid"

DEMO_PREFIX = "DEMO"

AS_OF = "2026-03-31"
DATASET_ID = "ds-demo-2026"
PERIOD = "2026-Q1"
CURRENCY = "GBP"


# ---------------------------------------------------------------------------
# Small builders shared by the M10.1 test modules
#
# They live here rather than in one test module because unittest discovery runs with
# `tests/` as the top level, so a sibling test module is not importable by bare name.
# ---------------------------------------------------------------------------

TEST_DATASET = "ds-test"


def new_set(**kwargs):
    """An empty synthesis set with one registered dataset to point provenance at."""
    kwargs.setdefault("subject", "test")
    result = synthesis_mod.SynthesisSet(**kwargs)
    result.register_dataset(TEST_DATASET, label="test.csv")
    return result


def dataset_ref():
    return synthesis_mod.ProvenanceRef(synthesis_mod.P_DATASET, TEST_DATASET,
                                       label="test.csv")


def demo_evidence(tier="C", publication_date="2026-06-01",
                  host="research.example.invalid", source="DEMO House",
                  claim_kind="market_sizing", content="A figure."):
    """One synthetic evidence item. The host is reserved and can never resolve."""
    return evidence_mod.EvidenceItem(
        source=source, reference="https://%s/a" % host, source_tier=tier,
        retrieved_at="2026-09-14", publication_date=publication_date,
        source_type=evidence_mod.RESEARCH_HOUSE, content=content,
        claim_kind=claim_kind, as_of="2026-09-14")


def evidence_set_with(*items):
    evidence = evidence_mod.EvidenceSet(operation="op-test", subject="s",
                                        category="industry", disclosure_tier=0)
    for item in items:
        evidence.add(item)
    return evidence


def _finding(analysis_id, analysis_type, kind, statement, **kwargs):
    return analytics_contract.AnalysisFinding(
        analysis_id, analysis_type, kind, statement, **kwargs)


def internal_sales():
    """Revenue growth: one material movement, one immaterial one."""
    analysis = analytics_contract.AnalysisSet(
        "sales", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "sales.revenue.total", "sales", analytics_contract.CALCULATION,
        "Revenue for 2026-Q1 was 1,250,000 GBP, up 180,000 GBP on 2025-Q4.",
        metric="revenue", period=PERIOD, comparison_period="2025-Q4",
        observed=Decimal("1250000"), comparison=Decimal("1070000"),
        change=Decimal("180000"), change_pct=Decimal("16.82"),
        unit="currency", currency=CURRENCY, basis="sum(net_revenue)",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Absolute movement 180000 meets the 10000 threshold."))
    analysis.add(_finding(
        "sales.orders.total", "sales", analytics_contract.CALCULATION,
        "Order count for 2026-Q1 was 4,120, up 30 on 2025-Q4.",
        metric="orders", period=PERIOD, comparison_period="2025-Q4",
        observed=Decimal("4120"), comparison=Decimal("4090"),
        change=Decimal("30"), change_pct=Decimal("0.73"),
        unit="count", basis="count(order_id)",
        materiality=materiality_mod.NOT_MATERIAL,
        materiality_reason="Movement of 30 (0.73%) is below both thresholds."))
    analysis.limit("sales.dimension_absent", "channel",
                   "The dataset carries no channel column, so channel mix was not "
                   "analysed.")
    return analysis


def internal_margin():
    """Gross margin, in percentage points, with its own materiality basis."""
    analysis = analytics_contract.AnalysisSet(
        "financial", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "financial.gross_margin", "financial", analytics_contract.CALCULATION,
        "Gross margin for 2026-Q1 was 38.40%, up 2.60 percentage points on 2025-Q4.",
        metric="gross_margin", period=PERIOD, comparison_period="2025-Q4",
        observed=Decimal("38.40"), comparison=Decimal("35.80"),
        change=Decimal("2.60"), unit="percent", basis="gross_profit / revenue",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Margin moved 2.60pp, meeting the 2.0pp threshold."))
    return analysis


def internal_product():
    """One product finding, so the product domain is represented."""
    analysis = analytics_contract.AnalysisSet(
        "product", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "product.top.widget", "product", analytics_contract.CALCULATION,
        "Widget contributed 512,000 GBP of revenue in 2026-Q1, 40.96% of the total.",
        metric="revenue", dimension="product", dimension_value="Widget",
        period=PERIOD, observed=Decimal("512000"), share_pct=Decimal("40.96"),
        unit="currency", currency=CURRENCY, basis="sum(net_revenue) by product",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Represents 40.96% of total revenue (threshold 1%)."))
    return analysis


def internal_customer():
    """One customer finding, so the customer domain is represented."""
    analysis = analytics_contract.AnalysisSet(
        "customer", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "customer.repeat.rate", "customer", analytics_contract.CALCULATION,
        "312 of 480 customers active in 2026-Q1 had also purchased before, a repeat "
        "rate of 65.00%.",
        metric="repeat_rate", period=PERIOD, observed=Decimal("65.00"),
        unit="percent", basis="returning_customers / active_customers",
        materiality=materiality_mod.NOT_MATERIAL,
        materiality_reason="No prior-period comparison is available for this rate."))
    return analysis


def internal_forecast():
    """A forecast set carrying a horizon limitation, as a real short history would."""
    from bops.forecast import contract as forecast_contract
    analysis = forecast_contract.ForecastSet(
        "forecast", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "forecast.revenue.base", "forecast", analytics_contract.CALCULATION,
        "Base-scenario revenue for 2026-Q2 is projected at 1,310,000 GBP.",
        metric="revenue", period="2026-Q2", observed=Decimal("1310000"),
        unit="currency", currency=CURRENCY,
        basis="linear_trend, selected by backtest over 8 periods",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Projected movement exceeds the absolute threshold."))
    analysis.limit("forecast.horizon_reduced", "revenue",
                   "The requested horizon exceeded half the available history and was "
                   "reduced to one period.",
                   status=analytics_contract.INSUFFICIENT_DATA)
    return analysis


def internal_anomaly():
    """An anomaly set: one flagged deviation, described and never explained."""
    from bops.anomaly import contract as anomaly_contract
    analysis = anomaly_contract.AnomalySet(
        "anomaly", currency=CURRENCY, quality_grade="PASS",
        provenance={"source_name": "demo_sales_2026.csv"})
    analysis.add(_finding(
        "anomaly.cost.2026-02", "anomaly", analytics_contract.CALCULATION,
        "Cost of goods in 2026-02 was 318,000 GBP against a trailing baseline of "
        "241,000 GBP, a deviation of 31.95% above baseline.",
        metric="cost_of_goods", period="2026-02", observed=Decimal("318000"),
        comparison=Decimal("241000"), change=Decimal("77000"),
        change_pct=Decimal("31.95"), unit="currency", currency=CURRENCY,
        basis="robust_deviation against a 6-period trailing baseline",
        materiality=materiality_mod.MATERIAL,
        materiality_reason="Absolute movement 77000 meets the 10000 threshold."))
    analysis.limit("anomaly.baseline_short", "cost_of_goods",
                   "Only six trailing periods were available, which is the minimum for "
                   "this detector.")
    return analysis


def _demo_item(slug, source, title, content, publication_date=None,
               source_type=evidence_mod.RESEARCH_HOUSE, claim_kind="market_sizing"):
    return evidence_mod.EvidenceItem(
        source="%s %s" % (DEMO_PREFIX, source),
        reference="%s/%s" % (DEMO_HOST, slug),
        source_tier="C",
        retrieved_at=AS_OF,
        title=title,
        publication_date=publication_date,
        source_type=source_type,
        content=content,
        claim_kind=claim_kind,
        operation="demo-synthesis-fixture",
        as_of=AS_OF,
        notes=["Synthetic demo evidence. The reference domain is reserved and cannot "
               "resolve; this is not a real source."])


def external_industry():
    """Two synthetic sources that disagree because they define the industry differently.

    The disagreement is declared rather than inferred, which is the case ADR-0016 exists
    for: the figures are close enough that a numeric test would call them agreement, and
    they are not measuring the same thing at all.
    """
    evidence = evidence_mod.EvidenceSet(
        operation="demo-synthesis-fixture", subject="demo widget industry",
        category="industry", query_text="demo widget industry size and scope",
        disclosure_tier=0)

    narrow = evidence.add(_demo_item(
        "widget-industry-narrow", "Narrow Scope Research",
        "Demo widget industry, manufacture only",
        "Counting manufacture only, the demo widget industry was worth 310 USD bn in "
        "2025. Aftermarket and services are excluded.",
        publication_date="2026-01-15"))

    broad = evidence.add(_demo_item(
        "widget-industry-broad", "Broad Scope Research",
        "Demo widget industry, manufacture plus aftermarket",
        "Including aftermarket parts and maintenance services, the demo widget industry "
        "reached 330 USD bn in 2025.",
        publication_date="2026-02-01"))

    undated = evidence.add(_demo_item(
        "widget-industry-primer", "Undated Primer",
        "Demo widget industry primer",
        "The demo widget industry comprises component manufacturers, integrators and "
        "aftermarket service providers.",
        publication_date=None, source_type=evidence_mod.VENDOR,
        claim_kind="positioning"))

    evidence.record_conflict(
        "demo widget industry size, 2025",
        [sources_mod.SourcePosition(
            narrow.id, 310.0, narrow.source, narrow.source_tier,
            source_date=narrow.publication_date, unit="USD bn",
            definition="manufacture only", scope="global, 2025",
            freshness=narrow.freshness["freshness"]),
         sources_mod.SourcePosition(
            broad.id, 330.0, broad.source, broad.source_tier,
            source_date=broad.publication_date, unit="USD bn",
            definition="manufacture plus aftermarket and services",
            scope="global, 2025", freshness=broad.freshness["freshness"])],
        declared=True,
        reason=("The sources draw the industry boundary differently: one counts "
                "manufacture only, the other adds aftermarket parts and services."))

    return evidence, {"narrow": narrow.id, "broad": broad.id, "undated": undated.id}


def candidate_claims(evidence_ids):
    """One candidate claim, in exactly the shape `close_retrieval` produces."""
    return [{
        "statement": "DEMO Narrow Scope Research reports the demo widget industry at "
                     "310 USD bn in 2025, counting manufacture only.",
        "class": 3,
        "status": "candidate",
        "verified": False,
        "evidence_id": evidence_ids["narrow"],
        "source": "%s Narrow Scope Research" % DEMO_PREFIX,
        "citation": "%s/widget-industry-narrow" % DEMO_HOST,
        "source_date": "2026-01-15",
        "source_tier": "C",
        "material": True,
        "retrieved_at": AS_OF,
        "freshness": "current",
        "limitations": ["Candidate only: retrieved evidence is untrusted and this claim "
                        "is unverified."],
    }]


def build(include_external=True, include_claims=True):
    """Assemble the full cross-domain fixture and return it with its handles.

    Returns `(synthesis, handles)`. `handles` names the ids a test needs to assert
    against, so a test never has to guess a content-addressed id.
    """
    result = synthesis_mod.SynthesisSet(
        synthesis_type="cross_domain", subject="Demo cross-domain synthesis",
        as_of=AS_OF, business_model="b2b_product", currency=CURRENCY,
        quality_grade="PASS")
    result.register_dataset(DATASET_ID, label="demo_sales_2026.csv",
                            detail="Synthetic demo dataset; not real business data.")

    handles = {"dataset_id": DATASET_ID, "as_of": AS_OF, "period": PERIOD}

    internal = [
        (internal_sales(), synthesis_mod.ORIGIN_SALES),
        (internal_margin(), synthesis_mod.ORIGIN_FINANCIAL),
        (internal_product(), synthesis_mod.ORIGIN_PRODUCT),
        (internal_customer(), synthesis_mod.ORIGIN_CUSTOMER),
        (internal_forecast(), synthesis_mod.ORIGIN_FORECAST),
        (internal_anomaly(), synthesis_mod.ORIGIN_ANOMALY),
    ]
    produced = {}
    for analysis, origin in internal:
        items = synthesis_mod.from_analysis_set(
            result, analysis, origin, dataset_id=DATASET_ID,
            geography="United Kingdom", metric_definition="net revenue, ex-VAT",
            scope="whole business", methodology="transaction ledger aggregation")
        produced[origin] = [item.id for item in items]
    handles["internal"] = produced

    if include_external:
        evidence, evidence_ids = external_industry()
        synthesis_mod.register_external(result, evidence,
                                        synthesis_mod.ORIGIN_INDUSTRY)
        handles["evidence"] = evidence_ids
        handles["evidence_set"] = evidence

        sourced = synthesis_mod.sourced_statement(
            result, synthesis_mod.ORIGIN_INDUSTRY,
            "DEMO Narrow Scope Research reports the demo widget industry at 310 USD bn "
            "in 2025, counting manufacture only.",
            evidence_ids=[evidence_ids["narrow"]],
            metric="industry_size", metric_definition="manufacture only",
            period="2025", geography="global", currency="USD",
            scope="global", methodology="top-down",
            # ADR-0025: the source published "310 USD bn"; the statement carries the
            # canonical quantity. `source_unit` performs that decomposition here, at
            # construction, and never inside `compare()`.
            source_unit="USD bn", observed=Decimal("310"))
        handles["sourced_id"] = sourced.id

        undated_sourced = synthesis_mod.sourced_statement(
            result, synthesis_mod.ORIGIN_INDUSTRY,
            "An undated DEMO primer describes the industry as comprising component "
            "manufacturers, integrators and aftermarket service providers.",
            evidence_ids=[evidence_ids["undated"]],
            metric_definition="participant kinds", geography="global",
            scope="global")
        handles["undated_sourced_id"] = undated_sourced.id

        if include_claims:
            claims = result.register_claims(candidate_claims(evidence_ids))
            handles["claim_ids"] = [claim["claim_id"] for claim in claims]

    return result, handles
