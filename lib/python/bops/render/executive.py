"""Executive-style output for the Milestone 2 vertical slice.

Implements the presentation rules in `reference/output-standards.md`: locale-aware
formatting, evidential material visually distinct from generative, data-quality warnings
placed *before* the numbers rather than in a footnote, and every report stating its basis.

This is the minimum needed to prove the slice, not the full executive-report skill (M10).
"""

from decimal import Decimal, ROUND_HALF_UP

from .. import evidence
from ..kpi import registry as kpi_registry
from ..quality import checks as quality_checks

SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "JPY": "¥", "INR": "₹"}


def money(value, currency="USD", number_format="1,234.56"):
    """Format money. Rounds once, here, at presentation."""
    if value is None:
        return "n/a"
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = amount < 0
    digits = "{:,.2f}".format(abs(amount))
    if number_format == "1.234,56":
        digits = digits.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    elif number_format == "1 234,56":
        digits = digits.replace(",", " ").replace(".", ",")
    elif number_format == "1234.56":
        digits = digits.replace(",", "")
    symbol = SYMBOLS.get(currency, "")
    rendered = "%s%s" % (symbol, digits) if symbol else "%s %s" % (currency, digits)
    return "-%s" % rendered if negative else rendered


def percent(value, places=1):
    if value is None:
        return "n/a"
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * places)
    return "%s%%" % Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)


def points(value):
    """Margin movements are percentage points, never a percentage change."""
    if value is None:
        return "n/a"
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "%s%spp" % ("+" if amount > 0 else "", amount)


def _kpi_value(result, currency, number_format):
    if not result.available:
        return "—"
    if result.unit == "currency":
        return money(result.value, currency, number_format)
    if result.unit == "percent":
        return percent(result.value)
    return str(result.value)


def render(result, findings=None, title="Business Health Snapshot"):
    """Render a pipeline result as an executive-style report.

    `findings` are the judgement-bearing observations produced by the analysis skill; the
    engine supplies none of its own, because deciding what matters is not arithmetic.
    """
    lines = []
    add = lines.append

    config = result.config
    context = result.context
    currency = config.get("locale.currency", "USD")
    number_format = config.get("locale.number_format", "1,234.56")

    add("# %s" % title)
    add("")

    # ---- halted run: say so first, and show nothing that implies validity ----
    if result.halted:
        add("## ⛔ Analysis stopped")
        add("")
        add(result.halt_reason or "The analysis could not be completed.")
        add("")
        add("**No KPIs, findings or conclusions are reported.** Figures derived from this "
            "dataset would be misleading, so none were produced.")
        add("")
        add(_quality_section(result, heading="## What must be fixed"))
        add("")
        add(_basis_section(result, currency))
        return "\n".join(l for l in lines if l is not None)

    # ---- data quality first, before any number -------------------------
    if result.quality and result.quality.grade != quality_checks.PASS:
        add("> **Data quality: %s.** Read the caveats in *Data Quality* below before acting "
            "on these figures." % result.quality.grade)
        add("")

    # ---- business context ------------------------------------------------
    add("## Reporting basis")
    add("")
    trend = result.analysis.get("revenue_trend") or {}
    period = ("%s to %s" % (trend.get("first_period"), trend.get("last_period"))
              if trend.get("first_period") else "not determined")
    add("| | |")
    add("|---|---|")
    add("| Business | %s |" % (context.get("identity.business_name") or "_not provided_"))
    add("| Business model | %s |" % (context.get("identity.business_model")
                                     or "_not provided — KPI relevance filtering is off_"))
    add("| Industry | %s |" % (context.get("identity.industry") or "_not provided_"))
    add("| Reporting period | %s |" % period)
    add("| Currency | %s |" % currency)
    add("| Data source | %s |" % result.dataset.provenance()["source_name"])
    if result.dataset.reader_tier:
        add("| Reader | %s |" % result.dataset.reader_tier.name)
    add("| Data quality | %s |" % result.quality.grade)
    add("")

    missing = context.missing()
    if missing:
        add("_Business context not provided for: %s. These were not guessed; the analysis "
            "is narrowed accordingly._"
            % ", ".join("`%s`" % m.path for m in missing))
        add("")

    # ---- KPI scorecard ---------------------------------------------------
    grouped = kpi_registry.bucket(result.kpis)
    add("## KPI scorecard")
    add("")
    add("| KPI | Value | Status |")
    add("|---|---|---|")
    for kpi in grouped[kpi_registry.COMPUTED]:
        add("| %s | **%s** | computed |" % (kpi.label,
                                            _kpi_value(kpi, currency, number_format)))
    for kpi in grouped[kpi_registry.PARTIAL]:
        add("| %s | %s | partial |" % (kpi.label, _kpi_value(kpi, currency, number_format)))
    for kpi in grouped[kpi_registry.UNAVAILABLE]:
        add("| %s | — | **unavailable** |" % kpi.label)
    for kpi in grouped[kpi_registry.NOT_APPLICABLE]:
        add("| %s | — | **not applicable** |" % kpi.label)
    add("")

    if grouped[kpi_registry.UNAVAILABLE] or grouped[kpi_registry.NOT_APPLICABLE]:
        add("**Why some KPIs are absent** — these are different statements and should not "
            "be read the same way:")
        add("")
        for kpi in grouped[kpi_registry.UNAVAILABLE]:
            add("- *%s* — **unavailable.** %s" % (kpi.label, kpi.reason))
        for kpi in grouped[kpi_registry.NOT_APPLICABLE]:
            add("- *%s* — **not applicable.** %s" % (kpi.label, kpi.reason))
        add("")

    # ---- findings --------------------------------------------------------
    findings = findings or []
    positive = [f for f in findings if f.get("direction") == "positive"]
    negative = [f for f in findings if f.get("direction") == "negative"]
    neutral = [f for f in findings if f.get("direction") not in ("positive", "negative")]

    add("## Key findings")
    add("")
    if not findings:
        add("_No findings were produced._")
        add("")
    for heading, group in (("Positive", positive), ("Negative", negative),
                           ("Other observations", neutral)):
        if not group:
            continue
        add("### %s" % heading)
        add("")
        for finding in group:
            marker = "**[%s]**" % finding["label"]
            material = ""
            if finding.get("materiality") == "material":
                material = " _(material)_"
            elif finding.get("materiality") == "undetermined":
                material = " _(materiality undetermined)_"
            add("- %s %s%s" % (marker, finding["statement"], material))
            if finding.get("basis"):
                add("  - Basis: %s" % finding["basis"])
        add("")

    # ---- data quality ----------------------------------------------------
    add(_quality_section(result))
    add("")

    # ---- provenance ------------------------------------------------------
    add("## Provenance")
    add("")
    summary = result.ledger.summary()
    add("Every statement above carries its origin. %d claims recorded: %d evidential "
        "(measured or calculated), %d generative (interpretation)."
        % (summary["total"], summary["evidential"], summary["generative"]))
    add("")
    add("| Class | Count | Meaning |")
    add("|---|---|---|")
    for class_name, count in sorted(summary["by_class"].items()):
        meaning = {
            "user-provided data": "read directly from your file",
            "calculated metric": "computed by the engine from your data",
            "analytical interpretation": "our reading of the figures, not a measurement",
            "estimate / assumption": "assumed, and flagged as such",
            "recommendation": "a proposed action",
        }.get(class_name, "")
        add("| %s | %d | %s |" % (class_name, count, meaning))
    add("")

    calculated = result.ledger.of_class(evidence.CALCULATED)
    if calculated:
        add("**How each figure was calculated**")
        add("")
        for claim in calculated[:8]:
            add("- %s" % claim.statement)
            add("  - Formula: `%s`" % claim.formula)
    add("")

    # ---- confidence ------------------------------------------------------
    add("## Confidence and limitations")
    add("")
    add(_confidence_paragraph(result))
    add("")
    add(_basis_section(result, currency))

    return "\n".join(l for l in lines if l is not None)


def _quality_section(result, heading="## Data quality"):
    lines = [heading, ""]
    report = result.quality
    if report is None:
        lines.append("_No quality assessment was run._")
        return "\n".join(lines)

    lines.append("**Overall grade: %s** (%d rows checked)"
                 % (report.grade, report.rows_checked))
    lines.append("")
    if not report.findings:
        lines.append("No quality problems were detected across the four check families "
                     "(structure, missing values, duplicates, validity).")
        return "\n".join(lines)

    lines.append("| Severity | Family | Finding |")
    lines.append("|---|---|---|")
    for finding in report.findings:
        lines.append("| %s | %s | %s |" % (finding.severity, finding.family,
                                           finding.message))
    lines.append("")
    if report.warnings:
        lines.append("_These warnings apply to every figure in this report. They are not "
                     "footnotes: they travel with the numbers._")
    return "\n".join(lines)


def _confidence_paragraph(result):
    grade = result.quality.grade if result.quality else "unknown"
    unconfirmed = result.semantic_map.needs_confirmation() if result.semantic_map else []
    parts = []

    if grade == quality_checks.PASS:
        parts.append("Data quality passed all four check families, so the calculated "
                     "figures carry **HIGH** confidence: they are arithmetic over your "
                     "own data, reproducible from the same file.")
    else:
        parts.append("Data quality is graded **%s**, so calculated figures carry "
                     "**MEDIUM** confidence — the arithmetic is exact, but the inputs "
                     "have known problems listed above." % grade)

    if unconfirmed:
        parts.append("The following column mappings are unconfirmed and any figure "
                     "depending on them should be treated as provisional: %s."
                     % ", ".join("%s → %s" % (m.role, m.column) for m in unconfirmed))

    parts.append("Interpretations are labelled **[INTERPRETATION]** and are our reading of "
                 "the figures, not measurements.")

    if not result.context.has("identity.business_model"):
        parts.append("No business model is set, so KPI relevance filtering is off and "
                     "every KPI was attempted regardless of whether it suits this business.")

    parts.append("This analysis covers internal data only. No external research, "
                 "benchmarking or forecasting was performed.")
    return " ".join(parts)


def _basis_section(result, currency):
    lines = ["---", "",
             "_Basis: %s_" % _basis_line(result, currency)]
    return "\n".join(lines)


def _basis_line(result, currency):
    parts = []
    if result.dataset:
        provenance = result.dataset.provenance()
        parts.append("source `%s` (%d rows)" % (provenance["source_name"],
                                                provenance["rows"]))
        if result.dataset.reader_tier:
            parts.append("read via %s" % result.dataset.reader_tier.name)
    parts.append("currency %s" % currency)
    if result.config:
        threshold = result.config.get("materiality.percentage")
        source = result.config.source_of("materiality.percentage")
        parts.append("materiality %s%% / %s (from %s)"
                     % (threshold, result.config.get("materiality.absolute_amount"), source))
    if result.quality:
        parts.append("data quality %s" % result.quality.grade)
    parts.append("no external sources consulted")
    return "; ".join(parts) + "."
