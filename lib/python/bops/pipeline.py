"""The Milestone 2 vertical slice, wired end to end.

Runs steps 1-18 of `reference/analysis-framework.md` deterministically. The command
(`/business-health`) orchestrates and narrates; this module does the work, so no business
rule is implemented twice.

Two gates can stop the run:

  * the **quality gate** — a `CRITICAL` finding halts, because continuing would mislead;
  * the **disclosure gate** — not reachable here, since the slice performs no external
    research.

Milestone 2 covers steps 1-18 for internal data only. Steps 5 (external retrieval), 15
(recommendations) and the forecast/anomaly branches arrive in later milestones.
"""

from decimal import Decimal

from . import evidence, materiality
from . import mapping as mapping_mod
from .analytics import sales as sales_mod
from .analytics import segmentation as segmentation_mod
from .config import load_defaults, resolve as resolve_config
from .context import loader as context_loader
from .ingest import canonical as canonical_mod
from .ingest import readers
from .kpi import registry as kpi_registry
from .quality import checks as quality_checks


class PipelineResult:
    """Everything one run produced, including why it stopped if it did."""

    def __init__(self, dataset=None, semantic_map=None, quality=None, kpis=None,
                 context=None, config=None, analysis=None, ledger=None,
                 halted=False, halt_reason=None, halted_at=None, canonical=None,
                 analyses=None):
        self.dataset = dataset
        self.canonical = canonical
        self.semantic_map = semantic_map
        self.quality = quality
        self.kpis = kpis or {}
        self.context = context
        self.config = config
        self.analysis = analysis or {}
        self.ledger = ledger or evidence.Ledger()
        self.halted = halted
        self.halt_reason = halt_reason
        self.halted_at = halted_at
        # Milestone 6 analytical domains, populated only when `analyse()` is called. The
        # Milestone 2 health check does not need them and does not pay for them.
        self.analyses = dict(analyses or {})

    @property
    def succeeded(self):
        return not self.halted

    def as_dict(self):
        return {
            "halted": self.halted,
            "halted_at": self.halted_at,
            "halt_reason": self.halt_reason,
            "provenance": (self.canonical.provenance() if self.canonical
                           else (self.dataset.provenance() if self.dataset else None)),
            "semantic_map": self.semantic_map.as_dict() if self.semantic_map else None,
            "quality": self.quality.as_dict() if self.quality else None,
            "kpis": {k: v.as_dict() for k, v in self.kpis.items()},
            "analysis": self.analysis,
            "analyses": {name: a.as_dict() for name, a in self.analyses.items()},
            "ledger": self.ledger.as_dict(),
        }


def run(source_path, project_dir=None, user_dir=None, context_overrides=None,
        command_args=None, prefer_tier=None, sheet=None, kpi_ids=None,
        load_context_files=True):
    """Execute the vertical slice against one data file."""
    ledger = evidence.Ledger()

    # -- 1. objective + Business Context ------------------------------------
    context = context_loader.resolve(
        project_dir=project_dir, user_dir=user_dir, overrides=context_overrides,
        load_files=load_context_files)

    config = resolve_config(
        defaults=load_defaults(),
        user_context=None,
        project_context=context.values or None,
        command_args=command_args)

    # -- 4. inspect data ----------------------------------------------------
    dataset = readers.read(source_path, sheet_name=sheet, prefer_tier=prefer_tier)

    # Canonical view: profiled types, currency evidence and per-field sensitivity.
    # Derived only - the source file is never touched.
    canonical = canonical_mod.build(dataset)

    tier_note = ""
    if dataset.reader_tier is not None:
        tier_note = " via %s" % dataset.reader_tier.name
    ledger.record(
        "Loaded %d rows and %d columns from %s%s."
        % (dataset.row_count, dataset.column_count,
           dataset.provenance()["source_name"], tier_note),
        evidence.USER_DATA, source=canonical.provenance(), confidence=evidence.HIGH)

    never_external = canonical.never_externalizable_columns()
    if never_external:
        ledger.record(
            "Column(s) %s are classified as never externalizable and will not be sent to "
            "any external service under any approval."
            % ", ".join(repr(c) for c in never_external),
            evidence.USER_DATA, source=canonical.provenance(), confidence=evidence.HIGH)

    if not canonical.complete:
        ledger.add_global_caveat(
            "Only %d of %d rows were examined (%s processing); figures describe the "
            "examined portion." % (canonical.rows_examined, canonical.row_count,
                                   canonical.processing_mode))

    for warning in canonical.warnings:
        ledger.add_global_caveat("Data: %s" % warning)

    # -- 4b. semantic mapping -----------------------------------------------
    semantic_map = mapping_mod.infer(dataset)
    for role, mapping in sorted(semantic_map.mappings.items()):
        if mapping.status == mapping_mod.AUTO:
            ledger.record(
                "Column %r identified as %s (confidence %.2f)."
                % (mapping.column, role, mapping.confidence),
                evidence.USER_DATA, source=dataset.provenance(), confidence=evidence.HIGH)
        else:
            ledger.record(
                "Column %r is only provisionally identified as %s (confidence %.2f) and "
                "requires confirmation." % (mapping.column, role, mapping.confidence),
                evidence.ASSUMPTION, confidence=evidence.LOW,
                caveats=["Unconfirmed column mapping"])

    # -- 6. QUALITY GATE ----------------------------------------------------
    quality = quality_checks.run(dataset, semantic_map, config,
                                 canonical=canonical, context=context)

    for finding in quality.warnings:
        ledger.add_global_caveat("Data quality: %s" % finding.message)

    if quality.halted:
        ledger.record(
            quality.halt_reason(), evidence.USER_DATA,
            source=dataset.provenance(), confidence=evidence.HIGH)
        return PipelineResult(
            dataset=dataset, canonical=canonical, semantic_map=semantic_map,
            quality=quality, context=context, config=config, ledger=ledger,
            halted=True, halted_at="quality_gate", halt_reason=quality.halt_reason())

    # -- 8. calculate (deterministic engine) --------------------------------
    kpis = kpi_registry.calculate(dataset, semantic_map, context, config, kpi_ids,
                                 canonical=canonical, quality=quality)
    for result in kpis.values():
        if result.status == kpi_registry.COMPUTED:
            ledger.record(
                "%s = %s" % (result.label, result.value),
                evidence.CALCULATED, formula=result.formula, inputs=result.inputs_used,
                confidence=(evidence.HIGH if quality.grade == quality_checks.PASS
                            else evidence.MEDIUM))
        elif result.status == kpi_registry.PARTIAL:
            ledger.record(
                "%s = %s (computed from an incomplete pass)" % (result.label, result.value),
                evidence.CALCULATED, formula=result.formula, inputs=result.inputs_used,
                confidence=evidence.MEDIUM, caveats=list(result.caveats))
        elif result.status == kpi_registry.NOT_APPLICABLE:
            ledger.record("%s: %s" % (result.label, result.reason),
                          evidence.INTERPRETATION, confidence=evidence.HIGH,
                          based_on=[])
        else:
            ledger.record("%s: %s" % (result.label, result.reason),
                          evidence.USER_DATA, source=dataset.provenance(),
                          confidence=evidence.HIGH)

    # -- 9-11. compare, materiality, investigate ----------------------------
    analysis = _analyse(dataset, semantic_map, kpis, config, ledger, quality)

    return PipelineResult(
        dataset=dataset, canonical=canonical, semantic_map=semantic_map, quality=quality,
        kpis=kpis, context=context, config=config, analysis=analysis, ledger=ledger)


def analyse(result, domains=None, presentation=None, record=True):
    """Run the Milestone 6 analytical domains over a completed pipeline result.

    Separate from `run()` on purpose. The Milestone 2 health check is a different, smaller
    job, and loading four domains of analysis into it would change what `/business-health`
    does. A caller that wants the analytics layer asks for it.

    `domains` names a subset (`("sales", "customer")`); the default is all four. Findings
    are appended to the evidence ledger with their provenance class intact unless
    `record` is false.
    """
    from . import analytics as analytics_mod

    presentation = presentation or analytics_mod.LOCAL
    wanted = dict(analytics_mod.DOMAINS)
    names = list(domains) if domains else [name for name, _fn in analytics_mod.DOMAINS]

    for name in names:
        runner = wanted.get(name)
        if runner is None:
            raise KeyError("unknown analytical domain %r; known: %s"
                           % (name, ", ".join(sorted(wanted))))
        analysis_set = runner(result, presentation=presentation)
        result.analyses[name] = analysis_set
        if record:
            analysis_set.record_in(result.ledger)
    return result.analyses


def forecast(result, targets=None, horizon=None, presentation=None, method_id=None,
             record=True):
    """Run the Milestone 8 forecasting layer over a completed pipeline result.

    Separate from `analyse()` for the same reason `analyse()` is separate from `run()`: a
    forecast is a different question, it is refused far more often than a historical
    analysis, and a caller that wants an estimate about the future asks for one.

    The returned `ForecastSet` is stored under `analyses["forecast"]` so every existing
    consumer of an `AnalysisSet` - materiality filtering, ledger recording, command
    rendering - reads it without change. Its findings carry provenance class 6, so the
    ledger keeps them visibly apart from measured history.
    """
    from . import analytics as analytics_mod
    from .forecast import engine as forecast_engine

    presentation = presentation or analytics_mod.LOCAL
    forecast_set = forecast_engine.run(
        result, targets=targets, horizon=horizon, presentation=presentation,
        method_id=method_id)
    result.analyses["forecast"] = forecast_set
    if record:
        forecast_set.record_in(result.ledger)
        forecast_set.assumption_register().record_in(result.ledger)
    return forecast_set


def detect_anomalies(result, metrics=None, presentation=None, sensitivity=None,
                     record=True):
    """Run the Milestone 8 anomaly scan over a completed pipeline result.

    Stored under `analyses["anomaly"]`, for the same reason as `forecast()`. Anomaly
    findings are ordinary `CALCULATION` claims - the deviation is measured, not modelled -
    so they enter the ledger as evidential rather than generative.
    """
    from . import analytics as analytics_mod
    from .anomaly import engine as anomaly_engine

    presentation = presentation or analytics_mod.LOCAL
    anomaly_set = anomaly_engine.run(
        result, metrics=metrics, presentation=presentation, sensitivity=sensitivity)
    result.analyses["anomaly"] = anomaly_set
    if record:
        anomaly_set.record_in(result.ledger)
    return anomaly_set


def _analyse(dataset, semantic_map, kpis, config, ledger, quality):
    """Deterministic comparisons and materiality verdicts (steps 9-11)."""
    analysis = {}
    confidence = (evidence.HIGH if quality.grade == quality_checks.PASS
                  else evidence.MEDIUM)

    revenue_trend = sales_mod.trend(dataset, semantic_map)
    analysis["revenue_trend"] = revenue_trend

    if revenue_trend.get("direction"):
        verdict = materiality.assess_amount(
            "Revenue, later half vs earlier half",
            revenue_trend["later_total"], revenue_trend["earlier_total"], config)
        analysis["revenue_materiality"] = verdict
        ledger.record(
            "Revenue %s %s%% between %s and %s (%s)."
            % (revenue_trend["direction"], revenue_trend["change_pct"],
               revenue_trend["first_period"], revenue_trend["last_period"],
               verdict.outcome),
            evidence.CALCULATED,
            formula="(later half total - earlier half total) / earlier half total * 100",
            inputs={"earlier_total": str(revenue_trend["earlier_total"]),
                    "later_total": str(revenue_trend["later_total"])},
            confidence=confidence)

    margins = sales_mod.margin_series(dataset, semantic_map)
    analysis["margin_series"] = margins
    if len(margins) >= 4:
        # The half means come from the full-precision series, never from the rounded one above:
        # averaging monthly margins that were already rounded to 2 dp rounds twice, and gave
        # -2.84pp here where the financial analysis reports -2.85pp for the same data (R-16).
        # Rounding is applied once, at presentation (CLAUDE.md section 4).
        earlier, later = segmentation_mod.series_halves(
            segmentation_mod.margin_by_period(dataset, semantic_map))
        verdict = materiality.assess_margin("Gross margin", later, earlier, config)
        analysis["margin_materiality"] = verdict
        analysis["margin_earlier_pct"] = earlier
        analysis["margin_later_pct"] = later
        ledger.record(
            "Average gross margin moved from %.2f%% to %.2f%% (%s)."
            % (earlier, later, verdict.outcome),
            evidence.CALCULATED,
            formula="mean(monthly gross margin %) by half of the period range",
            inputs={"earlier_mean_pct": str(earlier.quantize(Decimal('0.01'))),
                    "later_mean_pct": str(later.quantize(Decimal('0.01')))},
            confidence=confidence)

    for role, name in ((mapping_mod.PRODUCT, "product"),
                       (mapping_mod.REGION, "region"),
                       (mapping_mod.SALESPERSON, "salesperson")):
        if not semantic_map.confirmed(role):
            continue
        ranked = sales_mod.by_dimension(dataset, semantic_map, role)
        split, earlier_periods, later_periods = sales_mod.period_split(
            dataset, semantic_map, role)
        analysis["%s_ranked" % name] = ranked
        analysis["%s_movers" % name] = sales_mod.movers(split)
        analysis["%s_periods" % name] = {"earlier": earlier_periods, "later": later_periods}

    # Materiality of each product's movement — the filter that decides what gets reported.
    total_revenue = None
    if kpis.get("revenue") and kpis["revenue"].available:
        total_revenue = kpis["revenue"].value

    product_verdicts = []
    for row in analysis.get("product_movers", []):
        verdict = materiality.assess_amount(
            "Product %s" % row["key"], row["later"], row["earlier"], config)
        product_verdicts.append((row, verdict))
    analysis["product_materiality"] = product_verdicts
    analysis["total_revenue"] = total_revenue
    return analysis
