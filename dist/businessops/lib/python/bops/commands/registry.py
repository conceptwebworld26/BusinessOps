"""The command registry — which command runs what, declared as data.

A command is a thin orchestrator: it sequences existing components and formats their
output. It owns no formula, no threshold and no policy. That is exactly why the sequencing
can be a table rather than code — each entry says which analytical domains to run, which
skill interprets the result, which metrics to foreground and which sections to render, and
nothing else.

`architecture.md` section 18 lists "an analysis domain — new Layer-2 skill + optional
command" and "an output format — new renderer in the engine" as registration-only
extension points requiring no ADR, which is what this module and its siblings are.

Two commands share one domain on purpose. `/profitability-analysis` and
`/cash-flow-analysis` both read the financial analysis, because profit and cash are two
questions about the same computation; splitting the engine to match the two questions would
give the same number two homes.
"""

from .. import mapping as mapping_mod

#: Section identifiers the renderer understands. Order here is the order they appear.
STATUS = "status"
BASIS = "basis"
KEY_FINDINGS = "key_findings"
KPIS = "kpis"
ANALYSIS = "analysis"
FORECAST = "forecast"
ANOMALY = "anomaly"
LIMITATIONS = "limitations"
DATA_QUALITY = "data_quality"
EVIDENCE = "evidence"

SECTION_ORDER = (STATUS, BASIS, KEY_FINDINGS, KPIS, ANALYSIS, FORECAST, ANOMALY,
                 LIMITATIONS, DATA_QUALITY, EVIDENCE)

#: The historical-analysis sections. Deliberately *not* `SECTION_ORDER`: a Milestone 7
#: command must not grow a forecast section simply because Milestone 8 defined one.
DEFAULT_SECTIONS = (STATUS, BASIS, KEY_FINDINGS, KPIS, ANALYSIS, LIMITATIONS,
                    DATA_QUALITY, EVIDENCE)

# -- which engine a command drives ------------------------------------------

#: Milestone 6 deterministic analytics, via `pipeline.analyse`.
ANALYTICS_ENGINE = "analytics"
#: Milestone 8 forecasting, via `pipeline.forecast`.
FORECAST_ENGINE = "forecast"
#: Milestone 8 anomaly detection, via `pipeline.detect_anomalies`.
ANOMALY_ENGINE = "anomaly"

ENGINES = (ANALYTICS_ENGINE, FORECAST_ENGINE, ANOMALY_ENGINE)


class CommandSpec:
    """One command's declaration. Data only — no behaviour beyond lookup."""

    __slots__ = ("command_id", "title", "purpose", "domains", "skill", "sections",
                 "required_roles", "kpi_focus", "cross_domain", "argument_hint",
                 "engine")

    def __init__(self, command_id, title, purpose, domains, skill=None,
                 sections=DEFAULT_SECTIONS, required_roles=(), kpi_focus=(),
                 cross_domain=False, argument_hint=None, engine=ANALYTICS_ENGINE):
        if engine not in ENGINES:
            raise ValueError("unknown command engine %r" % (engine,))
        self.command_id = command_id
        self.title = title
        self.purpose = purpose
        self.domains = tuple(domains)
        self.skill = skill
        self.sections = tuple(sections)
        self.required_roles = tuple(required_roles)
        self.kpi_focus = tuple(kpi_focus)
        self.cross_domain = cross_domain
        self.argument_hint = argument_hint
        self.engine = engine

    @property
    def path(self):
        """The markdown orchestrator that documents this command."""
        return "commands/%s.md" % self.command_id

    def as_dict(self):
        return {"command": "/%s" % self.command_id, "title": self.title,
                "purpose": self.purpose, "domains": list(self.domains),
                "skill": self.skill, "sections": list(self.sections),
                "required_roles": list(self.required_roles),
                "kpi_focus": list(self.kpi_focus), "engine": self.engine,
                "cross_domain": self.cross_domain, "path": self.path}

    def __repr__(self):
        return "CommandSpec(/%s -> %s)" % (self.command_id, self.skill or "cross-domain")


#: Profit-statement metrics, in the order a reader walks them.
PROFITABILITY_KPIS = (
    "revenue", "gross_profit", "gross_margin",
    "operating_profit", "operating_margin", "ebitda", "ebitda_margin",
    "return_on_investment",
)

#: Cash and balance-sheet metrics. Every one of these is commonly absent from a sales
#: extract, which is why the command's main job is explaining absence honestly.
CASH_FLOW_KPIS = (
    "burn_rate", "runway", "working_capital",
    "days_sales_outstanding", "days_payable_outstanding",
)

SALES_KPIS = ("revenue", "revenue_growth", "gross_profit", "gross_margin",
              "average_order_value")

CUSTOMER_KPIS = ("customer_lifetime_value", "customer_acquisition_cost",
                 "customer_retention", "customer_churn", "net_revenue_retention")

PRODUCT_KPIS = ("gross_margin", "inventory_turnover")


COMMANDS = (
    CommandSpec(
        "business-health",
        "Business Health Snapshot",
        "A concise cross-domain view: what the data supports across sales, customers, "
        "products and the profit statement, and what it does not.",
        domains=("sales", "customer", "product", "financial"),
        skill=None, cross_domain=True,
        required_roles=(mapping_mod.DATE, mapping_mod.REVENUE),
        kpi_focus=SALES_KPIS,
        argument_hint='"[path to .xlsx or .csv] [--sheet NAME] [--currency GBP]"'),

    CommandSpec(
        "sales-analysis",
        "Sales Analysis",
        "Revenue and order performance, dimension movement, mix shift, contribution and "
        "revenue concentration.",
        domains=("sales",), skill="bops-sales-intelligence",
        required_roles=(mapping_mod.DATE, mapping_mod.REVENUE),
        kpi_focus=SALES_KPIS,
        argument_hint='"[path to .xlsx or .csv] [--sheet NAME]"'),

    CommandSpec(
        "customer-analysis",
        "Customer Analysis",
        "Customer population, new versus returning, repeat behaviour, retention and churn, "
        "contribution, concentration and acquisition cohorts.",
        domains=("customer",), skill="bops-customer-intelligence",
        required_roles=(mapping_mod.DATE, mapping_mod.CUSTOMER),
        kpi_focus=CUSTOMER_KPIS,
        argument_hint='"[path to .xlsx or .csv] [--shareable]"'),

    CommandSpec(
        "product-analysis",
        "Product Analysis",
        "Product and category contribution, growth, mix, per-product margin, "
        "concentration and first-observed period.",
        domains=("product",), skill="bops-product-intelligence",
        required_roles=(mapping_mod.DATE, mapping_mod.PRODUCT),
        kpi_focus=PRODUCT_KPIS,
        argument_hint='"[path to .xlsx or .csv]"'),

    CommandSpec(
        "profitability-analysis",
        "Profitability Analysis",
        "The profit statement as far as the data supports it, margin movement in "
        "percentage points, the cost-to-revenue relationship and profit concentration.",
        domains=("financial",), skill="bops-financial-analysis",
        required_roles=(mapping_mod.DATE, mapping_mod.REVENUE),
        kpi_focus=PROFITABILITY_KPIS,
        argument_hint='"[path to .xlsx or .csv]"'),

    CommandSpec(
        "cash-flow-analysis",
        "Cash Flow Analysis",
        "Cash and working-capital metrics where the data supports them, and a precise "
        "statement of which are unavailable and what field each one needs.",
        domains=("financial",), skill="bops-financial-analysis",
        required_roles=(mapping_mod.DATE, mapping_mod.REVENUE),
        kpi_focus=CASH_FLOW_KPIS,
        argument_hint='"[path to .xlsx or .csv]"'),

    CommandSpec(
        "ask-business-data",
        "Ask Business Data",
        "Answer one question about the supplied business data by routing it to the metric "
        "or analysis that already computes it — or say precisely why it cannot be answered.",
        domains=(), skill=None,
        required_roles=(mapping_mod.DATE,),
        argument_hint='"<question> [path to .xlsx or .csv]"'),

    # -- Milestone 8 ---------------------------------------------------------

    CommandSpec(
        "revenue-forecast",
        "Revenue Forecast",
        "Forecast revenue and the other supported financial series from history, with "
        "base, upside and downside scenarios, a stated assumption register, a measured "
        "uncertainty band and a backtest of the method that produced it.",
        domains=(), skill="bops-forecasting", engine=FORECAST_ENGINE,
        sections=(STATUS, BASIS, FORECAST, KPIS, LIMITATIONS, DATA_QUALITY, EVIDENCE),
        required_roles=(mapping_mod.DATE, mapping_mod.REVENUE),
        kpi_focus=("revenue", "revenue_growth", "gross_profit"),
        argument_hint='"[path to .xlsx or .csv] [--horizon 6] [--target revenue]"'),

    CommandSpec(
        "anomaly-detection",
        "Anomaly Detection",
        "Scan the supported series for periods that deviate from their own historical "
        "baseline, name the baseline each was measured against, and attribute the "
        "deviation to the parts of the data underneath it.",
        domains=(), skill="bops-anomaly-detection", engine=ANOMALY_ENGINE,
        sections=(STATUS, BASIS, ANOMALY, LIMITATIONS, DATA_QUALITY, EVIDENCE),
        required_roles=(mapping_mod.DATE,),
        kpi_focus=(),
        argument_hint='"[path to .xlsx or .csv] [--sensitivity medium] [--shareable]"'),
)

BY_ID = {spec.command_id: spec for spec in COMMANDS}
COMMAND_IDS = tuple(spec.command_id for spec in COMMANDS)


def spec_for(command_id):
    """The declaration for one command, or None. Accepts a leading slash."""
    return BY_ID.get(str(command_id).lstrip("/"))


def require(command_id):
    spec = spec_for(command_id)
    if spec is None:
        raise KeyError("unknown command %r; known: %s"
                       % (command_id, ", ".join("/%s" % c for c in COMMAND_IDS)))
    return spec


def as_dict():
    """The machine-readable command catalogue."""
    return {"count": len(COMMANDS), "commands": [s.as_dict() for s in COMMANDS]}


def mapping_table():
    """Command → primary implementation, for documentation and for tests to assert."""
    return {"/%s" % s.command_id: (s.skill or ("cross-domain orchestration"
                                               if s.cross_domain
                                               else "routing over internal analytics"))
            for s in COMMANDS}
