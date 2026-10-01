"""Anomaly orchestration: scan the supported series, score each period, attribute, gate.

Seven stages, and the order matters:

    1 series        the mapped dataset becomes monthly series, one per supported metric
    2 baseline      what normal was, computed trailing-only
    3 deviation     observed minus baseline, scored in the detector's units
    4 status        normal / unusual, from the detector threshold
    5 materiality   the user's configured policy, applied unchanged
    6 attribution   which dimension members sit under the deviation
    7 privacy       every label passes the Milestone 3 policy before it is written

Stages 4 and 5 are independent, and a period is a `material_anomaly` only when both agree.
That is what keeps the output short: on a volatile series many periods are statistically
unusual and almost none of them matter.

Attribution answers *where*, never *why*. `architecture.md` calls this "contributor
attribution", and the word is exact - it attributes the arithmetic of the deviation to
parts of the data, and stops there.
"""

from decimal import Decimal

from .. import mapping as mapping_mod, materiality as materiality_mod
from ..analytics import domain as domain_mod, presentation as presentation_mod
from ..kpi import contract as kpi_contract, primitives as p
from . import contract, detectors as detectors_mod

ZERO = Decimal("0")

#: Trailing window for the rolling detectors. Twelve months is one seasonal cycle, so the
#: baseline sees a whole year of ordinary variation before calling anything unusual.
DEFAULT_WINDOW = 12

#: How many contributors to name for one anomalous period.
TOP_CONTRIBUTORS = 3


class Metric:
    """One scannable series: where it comes from and how it is named."""

    __slots__ = ("metric_id", "name", "role", "derived", "unit", "dimension_role")

    def __init__(self, metric_id, name, role=None, derived=None,
                 unit=kpi_contract.CURRENCY, dimension_role=None):
        self.metric_id = metric_id
        self.name = name
        self.role = role
        self.derived = derived
        self.unit = unit
        self.dimension_role = dimension_role

    def __repr__(self):
        return "Metric(%s)" % self.metric_id


#: The scannable metrics. Each names the semantic role it needs; a metric whose role is
#: unmapped is reported as unavailable rather than skipped silently.
METRICS = (
    Metric("revenue", "Revenue", role=mapping_mod.REVENUE),
    Metric("cost", "Cost", role=mapping_mod.COST),
    Metric("gross_profit", "Gross profit", derived="revenue_minus_cost"),
    Metric("gross_margin", "Gross margin", derived="margin_pct",
           unit=kpi_contract.PERCENT),
    Metric("operating_expense", "Operating expense", role=mapping_mod.OPERATING_EXPENSE),
    Metric("cash_balance", "Cash balance", role=mapping_mod.CASH_BALANCE),
    Metric("order_count", "Order volume", derived="order_count",
           unit=kpi_contract.COUNT, dimension_role=mapping_mod.ORDER_ID),
    Metric("active_customers", "Active customers", derived="entity_count",
           unit=kpi_contract.COUNT, dimension_role=mapping_mod.CUSTOMER),
)

BY_ID = {m.metric_id: m for m in METRICS}
METRIC_IDS = tuple(m.metric_id for m in METRICS)

#: Dimensions attribution may break an anomalous period down by, most useful first.
ATTRIBUTION_DIMENSIONS = (
    (mapping_mod.PRODUCT, "product"),
    (mapping_mod.CATEGORY, "category"),
    (mapping_mod.REGION, "region"),
    (mapping_mod.SALESPERSON, "salesperson"),
    (mapping_mod.CUSTOMER, "customer"),
)


def _series_for(metric, dataset, semantic_map):
    """(series, reason). Never reads a file - only the canonical dataset and the map."""
    if not semantic_map or not semantic_map.column_for(mapping_mod.DATE):
        return None, ("No column is mapped to a date, so no period series can be built.")

    if metric.role is not None:
        if not semantic_map.column_for(metric.role):
            return None, ("No column is mapped to %s, so %s cannot be scanned."
                          % (metric.role, metric.name.lower()))
        series = p.series_by_period(dataset, semantic_map, metric.role)
        return (series, None) if series else (
            None, "The %s column holds no numeric values in any dated period."
                  % metric.role)

    if metric.derived in ("revenue_minus_cost", "margin_pct"):
        if not semantic_map.column_for(mapping_mod.REVENUE):
            return None, "No column is mapped to revenue."
        if not semantic_map.column_for(mapping_mod.COST):
            return None, ("No column is mapped to cost, so %s cannot be scanned."
                          % metric.name.lower())
        revenue = dict(p.series_by_period(dataset, semantic_map, mapping_mod.REVENUE) or [])
        cost = dict(p.series_by_period(dataset, semantic_map, mapping_mod.COST) or [])
        shared = sorted(set(revenue) & set(cost))
        if not shared:
            return None, "No period carries both revenue and cost."
        if metric.derived == "revenue_minus_cost":
            return [(period, revenue[period] - cost[period]) for period in shared], None
        out = []
        for period in shared:
            if revenue[period] == ZERO:
                continue
            out.append((period, (revenue[period] - cost[period]) / revenue[period]
                        * Decimal("100")))
        return (out, None) if out else (
            None, "Every period with cost data has zero revenue, so margin is undefined.")

    if metric.derived == "order_count":
        counts = p.distinct_entities_per_period(dataset, semantic_map,
                                                mapping_mod.ORDER_ID)
        if not counts:
            return None, ("No column is mapped to an order identifier, so order volume "
                          "cannot be scanned.")
        return [(period, Decimal(len(members)))
                for period, members in sorted(counts.items())], None

    if metric.derived == "entity_count":
        counts = p.distinct_entities_per_period(dataset, semantic_map,
                                                mapping_mod.CUSTOMER)
        if not counts:
            return None, ("No column is mapped to a customer, so customer activity "
                          "cannot be scanned.")
        return [(period, Decimal(len(members)))
                for period, members in sorted(counts.items())], None

    return None, "No series builder is registered for %s." % metric.metric_id


def _attribute(dataset, semantic_map, policy, period, baseline_periods, deviation,
               comparable_units=True):
    """Which dimension members sit under an anomalous period's deviation.

    Compares each member's value in the anomalous period against its own mean across the
    baseline periods, and reports the largest movers. Purely arithmetic: it locates the
    deviation, it does not explain it.
    """
    date_column = semantic_map.column_for(mapping_mod.DATE)
    revenue_column = semantic_map.column_for(mapping_mod.REVENUE)
    if not date_column or not revenue_column or deviation is None:
        return []

    dimension = None
    for role, name in ATTRIBUTION_DIMENSIONS:
        if semantic_map.column_for(role):
            dimension = (role, name, semantic_map.column_for(role))
            break
    if dimension is None:
        return []
    role, name, column = dimension

    current, prior = {}, {}
    baseline_set = set(baseline_periods)
    for row in dataset.rows:
        key = p.period_key(row.get(date_column))
        if key is None:
            continue
        member = row.get(column)
        value = row.get(revenue_column)
        if member in (None, "") or not p.is_number(value):
            continue
        if key == period:
            current[member] = current.get(member, ZERO) + p.dec(value)
        elif key in baseline_set:
            prior.setdefault(member, []).append((key, p.dec(value)))

    if not current:
        return []

    scored = []
    for member, value in current.items():
        history = prior.get(member, [])
        totals = {}
        for key, amount in history:
            totals[key] = totals.get(key, ZERO) + amount
        expected = (sum(totals.values(), ZERO) / Decimal(len(totals))
                    if totals else ZERO)
        scored.append((member, value, expected, value - expected))

    # Rank by movement in the same direction as the period's own deviation, so a shortfall
    # names what fell rather than what happened to rise alongside it.
    forward = deviation >= ZERO
    scored.sort(key=lambda item: item[3], reverse=forward)
    selected = [item for item in scored if (item[3] >= ZERO) == forward][:TOP_CONTRIBUTORS]

    # A share is only meaningful when the contributor movement and the period's deviation
    # are in the same unit. Attribution is always measured in revenue, so for a metric
    # counted in orders or expressed in percentage points the ratio would divide currency
    # by orders - which produced shares like "14140% of the movement", a number that
    # answers nothing. Those metrics still name the members that moved; they just do not
    # claim a share of a deviation measured in something else.
    magnitude = deviation if deviation >= ZERO else -deviation
    comparable = comparable_units and magnitude != ZERO

    out = []
    for rank, (member, value, expected, movement) in enumerate(selected, start=1):
        label, redacted = policy.label(column, member, role=name, rank=rank)
        share = (movement / magnitude * Decimal("100")) if comparable else None
        out.append(contract.Contributor(
            name, label, value, baseline=expected, deviation=movement,
            share_pct=share, redacted=redacted))
    return out


def scan_series(series, metric, config, sensitivity=None, window=DEFAULT_WINDOW,
                currency=None, min_baseline=None, attribute=None):
    """Score every period of one series. The pure core: no dataset, no pipeline, no I/O.

    Returns `(observations, reason)`. `reason` is set only when nothing could be scanned.
    """
    sensitivity = sensitivity or detectors_mod.resolve_sensitivity(config)
    min_baseline = (min_baseline if min_baseline is not None
                    else int(config.get("anomaly.min_baseline_periods", 6))
                    if config else 6)

    if len(series) <= min_baseline:
        return [], ("%d periods of history is not enough to establish a baseline; at "
                    "least %d prior periods are required before any period can be called "
                    "unusual." % (len(series), min_baseline + 1))

    observations = []
    for index in range(len(series)):
        period, observed = series[index]
        if index < min_baseline:
            continue

        # Every adequate detector measures the period; only a triggering one may raise a
        # flag. A corroborating detector still gets to describe the period when nothing
        # triggered, so its reading is never hidden - it simply cannot manufacture a flag
        # on a window it is known to mishandle.
        best, corroborating = None, None
        for detector in detectors_mod.adequate(series, index):
            measured = detector.measure(series, index, window, sensitivity)
            if measured is None:
                continue
            baseline, deviation, deviation_pct, score, threshold = measured
            if score is None:
                continue
            exceeded = score >= threshold
            candidate = (detector, baseline, deviation, deviation_pct, score, threshold,
                         exceeded and detector.triggers)

            if not detector.triggers:
                if corroborating is None:
                    corroborating = candidate
                continue
            # Prefer a detector that flagged; among equals, the highest relative score.
            if best is None:
                best = candidate
            elif candidate[6] and not best[6]:
                best = candidate
            elif candidate[6] == best[6] and (score / threshold) > (best[4] / best[5]):
                best = candidate

        if best is None:
            best = corroborating
        if best is None:
            continue
        detector, baseline, deviation, deviation_pct, score, threshold, exceeded = best

        status = contract.UNUSUAL if exceeded else contract.NORMAL
        # A margin is judged in percentage points, an amount against the absolute and
        # relative thresholds. Both policies already exist; neither is restated here.
        if metric.unit == kpi_contract.PERCENT:
            verdict = materiality_mod.assess_margin(
                "%s %s" % (metric.name, period), observed, baseline.centre, config)
        else:
            verdict = materiality_mod.assess_amount(
                "%s %s" % (metric.name, period), observed, baseline.centre, config,
                unit="currency" if metric.unit == kpi_contract.CURRENCY else "count")
        if status == contract.UNUSUAL and verdict.is_material:
            status = contract.MATERIAL_ANOMALY

        caveats = []
        if baseline.spread in (None, ZERO):
            caveats.append(
                "The baseline for this period is flat, so the deviation is scored as a "
                "percentage change rather than against an observed spread.")
        if metric.unit == kpi_contract.PERCENT:
            caveats.append(
                "This metric is a percentage; the deviation is in percentage points of "
                "the metric, not currency.")

        observation = contract.Observation(
            metric.metric_id, period, observed, baseline,
            deviation=deviation, deviation_pct=deviation_pct, score=score,
            score_unit=detector.score_unit, threshold=threshold, status=status,
            direction=contract.ABOVE if deviation >= ZERO else contract.BELOW,
            materiality=verdict.outcome, materiality_reason=verdict.reason,
            method=detector.detector_id, metric_name=metric.name,
            currency=currency if metric.unit == kpi_contract.CURRENCY else None,
            unit=metric.unit, caveats=caveats)

        if observation.flagged and attribute is not None:
            baseline_periods = [series[i][0]
                               for i in range(max(0, index - window), index)]
            observation.contributors = attribute(
                period, baseline_periods, deviation,
                metric.unit == kpi_contract.CURRENCY)
            if observation.contributors and metric.unit != kpi_contract.CURRENCY:
                observation.caveats.append(
                    "Contributors are measured in revenue, while this metric is not, so "
                    "they show where activity moved rather than a share of the deviation.")

        observations.append(observation)

    return observations, None


def run(result, metrics=None, presentation=presentation_mod.LOCAL, sensitivity=None,
        window=DEFAULT_WINDOW, attribute=True):
    """Scan every requested metric over one completed pipeline result.

    Returns an `AnomalySet`. A run halted by the quality gate produces no scan at all -
    `domain.prepare` enforces that, and calling an unvalidated dataset unusual would be
    exactly the silent degradation the architecture forbids.
    """
    analysis, context = domain_mod.prepare(result, "anomaly", presentation=presentation)
    wanted = [BY_ID[m] for m in metrics] if metrics else list(METRICS)

    config = result.config
    sensitivity = sensitivity or detectors_mod.resolve_sensitivity(config)
    min_baseline = int(config.get("anomaly.min_baseline_periods", 6)) if config else 6

    aset = contract.AnomalySet.adopt(
        analysis, sensitivity=sensitivity, min_baseline_periods=min_baseline)

    if context is None:                       # halted at the quality gate
        return aset

    policy = context.policy
    currency = context.currency

    def attribution(period, baseline_periods, deviation, comparable_units=True):
        return _attribute(result.dataset, result.semantic_map, policy, period,
                          baseline_periods, deviation, comparable_units)

    for metric in wanted:
        series, reason = _series_for(metric, result.dataset, result.semantic_map)
        if series is None:
            aset.scanned_metrics[metric.metric_id] = contract.UNAVAILABLE
            aset.limit("metric_unavailable", metric.name, reason,
                       status=contract.UNAVAILABLE)
            continue

        observations, scan_reason = scan_series(
            series, metric, config, sensitivity=sensitivity, window=window,
            currency=currency, min_baseline=min_baseline,
            attribute=attribution if attribute else None)

        if scan_reason:
            aset.scanned_metrics[metric.metric_id] = contract.INSUFFICIENT_DATA
            aset.limit("insufficient_history", metric.name, scan_reason,
                       status=contract.INSUFFICIENT_DATA)
            continue

        aset.scanned_metrics[metric.metric_id] = contract.AVAILABLE
        for observation in observations:
            aset.observe(observation)

    aset.note_primitive("kpi.primitives.series_by_period")
    if not any(v == contract.AVAILABLE for v in aset.scanned_metrics.values()):
        aset.status = contract.UNAVAILABLE
        aset.reason = ("No metric could be scanned for anomalies. Each limitation below "
                       "names the field or the history it needed.")
    return aset
