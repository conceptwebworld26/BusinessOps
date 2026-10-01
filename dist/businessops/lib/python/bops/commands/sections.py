"""Rendering a command result into the sections `reference/output-standards.md` requires.

The structured `CommandResult` is the artifact; this is one view of it. Nothing is computed
here — every figure is read from a `KPIResult` or an `AnalysisFinding` and formatted once,
at presentation, by the shared formatters in `bops.render`.

Two rules from the output standards shape the layout:

  * a data-quality warning appears **before** the numbers, never as a footnote;
  * `unavailable` and `not_applicable` are different statements and are never rendered as
    the same blank cell.

`/business-health` is deliberately rendered by embedding the Milestone 2 executive report
rather than by re-laying-out its content. That report is the behaviour the vertical slice
proves, and reproducing its sections here would be a second implementation of the same
output — so the cross-domain material is *added* around it instead.
"""

from .. import evidence as evidence_mod
from .. import materiality as materiality_mod
from .. import render as render_mod
from ..analytics import contract as analytics_contract
from ..kpi import contract as kpi_contract
from ..quality import contract as quality_contract
from . import query as query_mod
from . import registry as registry_mod
from . import runner as runner_mod

STATUS_LABEL = {
    analytics_contract.AVAILABLE: "available",
    analytics_contract.UNAVAILABLE: "unavailable",
    analytics_contract.NOT_APPLICABLE: "not applicable",
    analytics_contract.INSUFFICIENT_DATA: "insufficient data",
}


def _kpi_cell(result, currency, number_format):
    if result is None:
        return "—"
    if not result.available:
        return "—"
    if result.unit == kpi_contract.CURRENCY:
        return render_mod.money(result.value, result.currency or currency, number_format)
    if result.unit == kpi_contract.PERCENT:
        return render_mod.percent(result.value, places=2)
    if result.unit == kpi_contract.DAYS:
        return "%s days" % render_mod.percent(result.value, places=1).rstrip("%")
    return str(result.value)


def _formats(command_result):
    config = command_result.config
    currency = command_result.currency or "USD"
    number_format = (config.get("locale.number_format", "1,234.56")
                     if config is not None else "1,234.56")
    return currency, number_format


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def status_section(command_result):
    spec = command_result.spec
    lines = ["# %s" % spec.title, ""]
    if command_result.status == "halted":
        lines += ["## ⛔ Analysis stopped", "",
                  command_result.reason or "The analysis could not be completed.", "",
                  "**No KPIs, findings or conclusions are reported.** Figures derived from "
                  "this dataset would be misleading, so none were produced.", ""]
        return "\n".join(lines)
    if command_result.status != "ok":
        lines += ["## Not available", "",
                  command_result.reason or "This command could not be run.", ""]
        if command_result.error_type:
            lines += ["_Reported as `%s`._" % command_result.error_type, ""]
        return "\n".join(lines)

    grade = command_result.quality_grade
    if grade and grade != quality_contract.PASS:
        lines += ["> **Data quality: %s.** Read *Data quality* below before acting on "
                  "these figures." % grade, ""]
    lines += ["**Status:** %s · %d finding(s), %d of them material · %d limitation(s)."
              % (command_result.status, len(command_result.findings()),
                 len(command_result.material_findings()),
                 len(command_result.limitations())), ""]

    coverage = command_result.focus_coverage()
    if coverage["status"] in (runner_mod.NONE_AVAILABLE, runner_mod.PARTIAL,
                              runner_mod.NOT_APPLICABLE):
        lines += [_coverage_line(command_result.spec, coverage), ""]
    return "\n".join(lines)


def _coverage_line(spec, coverage):
    """Say plainly how much of this command's own subject the data could support."""
    if coverage["status"] == runner_mod.NONE_AVAILABLE:
        return ("> **%s is unavailable from this dataset.** None of the %d metric(s) this "
                "command reports could be produced: %s. What follows is context from the "
                "same data, not a substitute for them."
                % (spec.title, coverage["total"], ", ".join(coverage["missing"])))
    if coverage["status"] == runner_mod.NOT_APPLICABLE:
        return ("> **%s does not apply to this business model.** %s"
                % (spec.title, ", ".join(coverage["not_applicable"])))
    absent = coverage["missing"] + coverage["not_applicable"]
    return ("> **%s is partial:** %d of %d metric(s) were produced. Absent: %s. Each is "
            "explained under *KPIs* with the field it needs."
            % (spec.title, coverage["available"], coverage["total"], ", ".join(absent)))


def basis_section(command_result):
    context = command_result.context
    currency, _fmt = _formats(command_result)
    result = command_result.result
    lines = ["## Reporting basis", "", "| | |", "|---|---|"]
    if context is not None:
        lines.append("| Business | %s |"
                     % (context.get("identity.business_name") or "_not provided_"))
        lines.append("| Business model | %s |"
                     % (context.get("identity.business_model")
                        or "_not provided — KPI relevance filtering is off_"))
        lines.append("| Industry | %s |"
                     % (context.get("identity.industry") or "_not provided_"))
    periods, comparison = None, None
    for analysis in command_result.analyses.values():
        periods = periods or analysis.periods
        comparison = comparison or analysis.comparison_periods
    if periods:
        lines.append("| Reporting period | %s to %s |" % (periods[0], periods[-1]))
    if comparison:
        lines.append("| Comparison window | %s..%s versus %s..%s |"
                     % (comparison["earlier"][0], comparison["earlier"][-1],
                        comparison["later"][0], comparison["later"][-1]))
    lines.append("| Currency | %s |" % currency)
    if result is not None and result.dataset is not None:
        lines.append("| Data source | %s |"
                     % result.dataset.provenance()["source_name"])
        lines.append("| Rows | %d |" % result.dataset.row_count)
        if result.dataset.reader_tier:
            lines.append("| Reader | %s |" % result.dataset.reader_tier.name)
    if result is not None and result.canonical is not None:
        lines.append("| Processing mode | %s%s |"
                     % (result.canonical.processing_mode,
                        "" if result.canonical.complete else " (incomplete pass)"))
    if command_result.quality_grade:
        lines.append("| Data quality | %s |" % command_result.quality_grade)
    lines.append("| Presentation | %s |" % command_result.presentation)
    lines.append("")

    if context is not None:
        missing = context.missing()
        if missing:
            lines += ["_Business context not provided for: %s. These were not guessed._"
                      % ", ".join("`%s`" % m.path for m in missing), ""]
    return "\n".join(lines)


def _deduplicate(findings):
    """Collapse identical statements produced by more than one domain.

    Revenue concentration is computed by the sales, customer and financial analyses because
    each needs it for its own purpose. Each recording it is correct; printing it three times
    in one report is not.
    """
    seen, out = set(), []
    for finding in findings:
        if finding.statement in seen:
            continue
        seen.add(finding.statement)
        out.append(finding)
    return out


def key_findings_section(command_result):
    lines = ["## Key findings", ""]
    findings = _deduplicate(command_result.findings())
    if not findings:
        lines += ["_No findings were produced. See *Limitations* for why._", ""]
        return "\n".join(lines)

    material = [f for f in findings
                if f.materiality == materiality_mod.MATERIAL]
    others = [f for f in findings if f not in material]

    if material:
        lines += ["### Material movements", ""]
        for finding in material:
            lines.append("- **[%s]** %s _(material)_"
                         % (finding.finding_type, finding.statement))
            lines.append("  - Basis: %s" % finding.basis)
    else:
        lines += ["_No movement met the materiality thresholds. That is a result, not an "
                  "absence of analysis._", ""]

    if others:
        lines += ["", "### Other observations", ""]
        for finding in others:
            suffix = ""
            if finding.materiality == materiality_mod.UNDETERMINED:
                suffix = " _(materiality undetermined)_"
            lines.append("- **[%s]** %s%s"
                         % (finding.finding_type, finding.statement, suffix))
    lines.append("")
    return "\n".join(lines)


def kpi_section(command_result):
    spec = command_result.spec
    currency, number_format = _formats(command_result)
    lines = ["## KPIs", ""]
    focus = command_result.focus_kpis()
    if not focus:
        lines += ["_This command foregrounds no fixed metric set._", ""]
        return "\n".join(lines)

    lines += ["| KPI | Value | Status |", "|---|---|---|"]
    absent = []
    for kpi_id, result in focus:
        if result is None:
            lines.append("| `%s` | — | **not computed** |" % kpi_id)
            continue
        label = STATUS_LABEL.get(result.status, result.status)
        lines.append("| %s | %s | %s |"
                     % (result.label, _kpi_cell(result, currency, number_format),
                        "**%s**" % label if not result.available else label))
        if not result.available:
            absent.append(result)
    lines.append("")

    if absent:
        lines += ["**Why some metrics are absent** — these are different statements and "
                  "must not be read the same way:", ""]
        for result in absent:
            lines.append("- *%s* — **%s.** %s"
                         % (result.label, STATUS_LABEL.get(result.status, result.status),
                            result.reason))
        lines.append("")
    return "\n".join(lines)


def analysis_section(command_result):
    lines = ["## Analysis", ""]
    if not command_result.analyses:
        lines += ["_No analytical domain was run for this command._", ""]
        return "\n".join(lines)

    lines += ["| Domain | Status | Findings | Limitations | Dimensions covered |",
              "|---|---|---|---|---|"]
    for name in command_result.spec.domains:
        analysis = command_result.analyses.get(name)
        if analysis is None:
            continue
        lines.append("| %s | %s | %d | %d | %s |"
                     % (name, STATUS_LABEL.get(analysis.status, analysis.status),
                        len(analysis.findings), len(analysis.limitations),
                        ", ".join(analysis.dimensions_covered) or "—"))
    lines.append("")

    for name in command_result.spec.domains:
        analysis = command_result.analyses.get(name)
        if analysis is None or not analysis.dimensions_skipped:
            continue
        lines.append("_%s: %s_" % (name.title(),
                                   " ".join(sorted(analysis.dimensions_skipped.values()))))
        lines.append("")
    return "\n".join(lines)


def forecast_section(command_result):
    """The forecast view: what was estimated, under what assumptions, with what error.

    Ordered so a reader meets the caveats before the numbers. The scenario table comes
    after the method and its backtest, because a total with no method behind it is the
    thing this whole layer exists to avoid.
    """
    from ..forecast import contract as forecast_contract

    lines = ["## Forecast", ""]
    forecast_set = command_result.forecast_set
    if forecast_set is None:
        lines += ["_No forecast was produced for this command._", ""]
        return "\n".join(lines)

    lines += ["> Every figure in this section is an **estimate** (evidence class 6), not a "
              "measured result. Forecasts are never merged with actuals.", ""]

    lines += ["| Target | Status | Method | History | Horizon |", "|---|---|---|---|---|"]
    for metric in sorted(forecast_set.forecasts):
        item = forecast_set.forecasts[metric]
        lines.append("| %s | %s | %s | %s | %s |"
                     % (item.metric_name,
                        STATUS_LABEL.get(item.status, item.status),
                        item.method_name or "—",
                        "%d periods" % item.history_periods if item.history_periods
                        else "—",
                        "%d periods" % item.horizon if item.horizon else "—"))
    lines.append("")

    for metric in sorted(forecast_set.forecasts):
        item = forecast_set.forecasts[metric]
        if not item.available:
            continue
        lines += ["### %s — %s" % (item.metric_name, item.forecast_period), ""]
        lines += ["**Method.** %s" % (item.method_rationale or item.method_name), ""]
        lines += ["**Validation.** %s" % item.validation.statement(), ""]
        lines += ["**Uncertainty.** %s" % item.uncertainty.statement(), ""]

        lines += ["| Scenario | Assumption | Total (%s) |" % (item.currency or "value"),
                  "|---|---|---|"]
        for name in forecast_contract.SCENARIOS:
            scenario = item.scenario(name)
            if scenario is None:
                continue
            assumption = (scenario.assumption.statement if scenario.assumption
                          else "—")
            lines.append("| %s | %s | %s |"
                         % (name, assumption,
                            forecast_contract.money(scenario.total(), item.currency)))
        lines.append("")

        base = item.base()
        if base is not None:
            lines += ["| Period | Base | Low | High |", "|---|---|---|---|"]
            for point in base.points:
                lines.append("| %s | %s | %s | %s |"
                             % (point.period,
                                forecast_contract.money(point.value, item.currency),
                                forecast_contract.money(point.low, item.currency),
                                forecast_contract.money(point.high, item.currency)))
            lines.append("")

        if len(item.assumptions):
            lines += ["**Assumption register.**", ""]
            for assumption in item.assumptions:
                lines.append("- %s" % assumption.statement)
            lines.append("")

    return "\n".join(lines)


def anomaly_section(command_result):
    """The anomaly view: what was scanned, what stood out, and against which baseline."""
    from ..anomaly import contract as anomaly_contract

    lines = ["## Anomalies", ""]
    anomaly_set = command_result.anomaly_set
    if anomaly_set is None:
        lines += ["_No anomaly scan was run for this command._", ""]
        return "\n".join(lines)

    lines += ["> %s" % anomaly_contract.INVESTIGATION_NOTE, ""]

    scanned = anomaly_set.scanned_metrics
    if scanned:
        lines += ["| Metric | Scan | Periods checked | Flagged |",
                  "|---|---|---|---|"]
        for metric in sorted(scanned):
            observations = anomaly_set.by_metric(metric)
            flagged = [o for o in observations if o.flagged]
            lines.append("| %s | %s | %d | %d |"
                         % (metric, STATUS_LABEL.get(scanned[metric], scanned[metric]),
                            len(observations), len(flagged)))
        lines.append("")

    flagged = anomaly_set.flagged()
    if not flagged:
        lines += ["_No period deviated from its baseline by more than the configured "
                  "threshold. The scan ran; it found nothing unusual._", ""]
        return "\n".join(lines)

    lines += ["**Sensitivity: %s.** %d of %d checked periods were flagged."
              % (anomaly_set.sensitivity, len(flagged), len(anomaly_set.observations)),
              ""]
    def value_cell(observation, value):
        """A margin is shown as a percentage; an amount in its currency. Rendering a
        margin as a bare number leaves the reader to guess which it is."""
        if observation.unit == kpi_contract.PERCENT:
            return anomaly_contract.percent(value)
        return anomaly_contract.money(value, observation.currency)

    lines += ["| Period | Metric | Observed | Baseline | Deviation | Score | Status |",
              "|---|---|---|---|---|---|---|"]
    for observation in flagged:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                     % (observation.period, observation.metric_name,
                        value_cell(observation, observation.observed),
                        value_cell(observation, observation.baseline.centre
                                   if observation.baseline else None),
                        anomaly_contract.percent(observation.deviation_pct),
                        observation.score_text(),
                        observation.status.replace("_", " ")))
    lines.append("")

    with_contributors = [o for o in flagged if o.contributors]
    if with_contributors:
        lines += ["### Where the deviation sits", "",
                  "_Attribution locates a deviation in the data. It does not explain it._",
                  ""]
        for observation in with_contributors:
            # A share is only shown where the contributor movement and the deviation are
            # in the same unit; otherwise the member is named without a fabricated ratio.
            named = ", ".join(
                ("%s (%s of the movement)"
                 % (c.label, anomaly_contract.percent(c.share_pct))
                 if c.share_pct is not None else c.label)
                for c in observation.contributors)
            lines.append("- **%s, %s** — %s"
                         % (observation.period, observation.metric_name, named))
        lines.append("")
    return "\n".join(lines)


def limitations_section(command_result):
    lines = ["## Limitations", ""]
    items = command_result.limitations()
    if not items:
        lines += ["_Nothing was withheld: every analysis this command attempted "
                  "completed._", ""]
        return "\n".join(lines)

    grouped = {}
    for domain, item in items:
        grouped.setdefault(item.status, []).append((domain, item))
    for status in (analytics_contract.UNAVAILABLE, analytics_contract.NOT_APPLICABLE,
                   analytics_contract.INSUFFICIENT_DATA, analytics_contract.AVAILABLE):
        rows = grouped.get(status)
        if not rows:
            continue
        lines += ["### %s" % STATUS_LABEL.get(status, status).title(), ""]
        for domain, item in rows:
            lines.append("- **%s** (%s) — %s" % (item.subject, domain, item.reason))
        lines.append("")
    return "\n".join(lines)


def data_quality_section(command_result):
    report = command_result.quality
    lines = ["## Data quality", ""]
    if report is None:
        lines += ["_No quality assessment was run._", ""]
        return "\n".join(lines)
    lines += ["**Overall grade: %s** (%d rows checked)" % (report.grade,
                                                           report.rows_checked), ""]
    if not report.findings:
        lines += ["No quality problems were detected across the thirteen check families.",
                  ""]
        return "\n".join(lines)
    lines += ["| Severity | Family | Finding |", "|---|---|---|"]
    for finding in report.findings:
        lines.append("| %s | %s | %s |" % (finding.severity, finding.family,
                                           finding.message))
    lines.append("")
    if report.warnings:
        lines += ["_These warnings apply to every figure above. They are not footnotes: "
                  "they travel with the numbers._", ""]
    return "\n".join(lines)


def evidence_section(command_result):
    lines = ["## Evidence and provenance", ""]
    provenance = {}
    for analysis in command_result.analyses.values():
        provenance = analysis.provenance or provenance
        if provenance:
            break
    if provenance:
        lines += ["| | |", "|---|---|"]
        for key in ("source", "rows", "processing_mode", "complete", "reader_tier",
                    "quality_grade"):
            if key in provenance:
                lines.append("| %s | %s |" % (key.replace("_", " ").title(),
                                              provenance[key]))
        lines.append("")

    ledger = command_result.ledger
    if ledger is not None:
        summary = ledger.summary()
        lines += ["%d claims recorded: %d evidential (measured or calculated), %d "
                  "generative (interpretation or assumption). %d untraceable."
                  % (summary["total"], summary["evidential"], summary["generative"],
                     summary["untraceable"]), ""]

    calculated = [f for f in command_result.findings()
                  if f.finding_type == analytics_contract.CALCULATION][:8]
    if calculated:
        lines += ["**How the foregrounded figures were produced**", ""]
        for finding in calculated:
            lines.append("- %s" % finding.statement)
            lines.append("  - Basis: `%s`" % finding.basis)
            if finding.fields_used:
                lines.append("  - Fields: %s"
                             % ", ".join("`%s`" % f for f in finding.fields_used
                                         if f))
        lines.append("")

    caveats = []
    for analysis in command_result.analyses.values():
        for caveat in analysis.caveats:
            if caveat not in caveats:
                caveats.append(caveat)
    if caveats:
        lines += ["**Caveats carried by every figure above**", ""]
        lines += ["- %s" % caveat for caveat in caveats]
        lines.append("")

    confidences = {analysis.default_confidence
                   for analysis in command_result.analyses.values()}
    if confidences:
        lines += ["**Confidence:** %s. Calculated figures are arithmetic over your own "
                  "data; interpretation is the reading skill's, and is labelled as such. "
                  "This analysis covers internal data only — no external research, "
                  "benchmarking or forecasting was performed."
                  % "/".join(sorted(confidences)), ""]
    elif command_result.status == "ok":
        lines += ["**Confidence:** %s (no analytical domain was run)."
                  % (evidence_mod.HIGH
                     if command_result.quality_grade == quality_contract.PASS
                     else evidence_mod.MEDIUM), ""]
    return "\n".join(lines)


def answer_section(command_result):
    """The `/ask-business-data` reply: what was asked, where it went, what came back."""
    answer = command_result.answer
    routing = command_result.routing
    lines = ["## Answer", ""]
    if routing is None:
        lines += ["_No question was routed._", ""]
        return "\n".join(lines)

    lines += ["**Question:** %s" % (command_result.question or "_none supplied_"), ""]

    if answer is None or answer.status == query_mod.UNSUPPORTED:
        lines += ["**Not supported.** %s"
                  % (routing.reason or "This question is out of scope."), ""]
        return "\n".join(lines)

    if answer.status == query_mod.CLARIFICATION_NEEDED:
        lines += ["**Clarification needed.** %s" % answer.reason, ""]
        if routing.candidates:
            lines += ["Candidates: %s" % ", ".join("`%s`" % c
                                                   for c in routing.candidates), ""]
        return "\n".join(lines)

    if answer.status == query_mod.UNAVAILABLE:
        lines += ["**Cannot be answered from this data.** %s" % answer.reason, ""]
        if answer.kpi is not None:
            lines += ["_Routed to metric `%s`; the engine reported it as %s._"
                      % (answer.kpi.kpi_id,
                         STATUS_LABEL.get(answer.kpi.status, answer.kpi.status)), ""]
        return "\n".join(lines)

    currency, number_format = _formats(command_result)
    if answer.kpi is not None:
        result = answer.kpi
        lines += ["**%s** — %s" % (result.label,
                                   _kpi_cell(result, currency, number_format)), "",
                  "- Classification: `CALCULATION` (evidence class 4)",
                  "- Formula: `%s`" % result.formula,
                  "- Fields: %s" % ", ".join("`%s`" % f
                                             for f in sorted(result.definition.inputs))]
        if result.caveats:
            lines += ["- Caveats: %s" % "; ".join(result.caveats)]
        lines.append("")
    elif answer.finding is not None:
        finding = answer.finding
        lines += ["**[%s]** %s" % (finding.finding_type, finding.statement), "",
                  "- Basis: `%s`" % finding.basis,
                  "- Routed via: `%s` / %s" % (routing.domain, routing.intent)]
        if finding.materiality:
            lines.append("- Materiality: %s — %s"
                         % (finding.materiality, finding.materiality_reason))
        if finding.caveats:
            lines.append("- Caveats: %s" % "; ".join(finding.caveats))
        lines.append("")
        if answer.supporting:
            lines += ["Also computed for the same question:", ""]
            lines += ["- %s" % f.statement for f in answer.supporting]
            lines.append("")

    lines += ["_This is a calculated result read from the deterministic engine, not an "
              "interpretation. Interpretation, if you want it, is the relevant analysis "
              "skill's job._", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

RENDERERS = {
    registry_mod.STATUS: status_section,
    registry_mod.BASIS: basis_section,
    registry_mod.KEY_FINDINGS: key_findings_section,
    registry_mod.KPIS: kpi_section,
    registry_mod.ANALYSIS: analysis_section,
    registry_mod.FORECAST: forecast_section,
    registry_mod.ANOMALY: anomaly_section,
    registry_mod.LIMITATIONS: limitations_section,
    registry_mod.DATA_QUALITY: data_quality_section,
    registry_mod.EVIDENCE: evidence_section,
}


def render(command_result):
    """The full user-facing report for one command run."""
    if command_result.command_id == "business-health":
        return _render_health(command_result)

    blocks = [status_section(command_result)]
    if command_result.command_id == "ask-business-data":
        blocks.append(answer_section(command_result))

    if command_result.status in ("halted", "unavailable", "clarification_needed",
                                 "unsupported"):
        # Nothing analytical may be presented, but the reader still needs the basis and
        # the quality picture to know why.
        if command_result.result is not None:
            blocks.append(basis_section(command_result))
            blocks.append(data_quality_section(command_result))
        return "\n".join(block for block in blocks if block)

    for section in command_result.spec.sections:
        if section == registry_mod.STATUS:
            continue
        blocks.append(RENDERERS[section](command_result))
    return "\n".join(block for block in blocks if block)


def _render_health(command_result):
    """`/business-health` keeps the Milestone 2 executive report and adds to it.

    The vertical slice's report is the behaviour that was proven; re-laying it out here
    would be a second implementation of the same output. So it is embedded whole, and the
    cross-domain material is added after it.
    """
    from .. import analytics as analytics_mod

    if command_result.result is None:
        return status_section(command_result)

    result = command_result.result
    currency, number_format = _formats(command_result)
    findings = analytics_mod.build_findings(
        result, lambda value: render_mod.money(value, currency, number_format))
    report = render_mod.render(result, findings)

    if command_result.status != "ok":
        return report

    blocks = [report, "", "---", "",
              analysis_section(command_result),
              key_findings_section(command_result),
              limitations_section(command_result)]
    return "\n".join(block for block in blocks if block)
