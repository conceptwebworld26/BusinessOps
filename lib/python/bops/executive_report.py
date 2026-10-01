# -*- coding: utf-8 -*-
"""Executive Report: an assembly of existing artifacts over one synthesis set (ADR-0033).

An executive report is the most condensed and most-forwarded artifact BusinessOps produces, and
so the one where a provenance failure would do the most damage (ADR-0022). The response here is
to author nothing. Every business statement the report shows is a statement the synthesis set
already holds, a class-7 record a `StrategyResult` already carries, or a part of a decision
package a `DecisionResult` already carries - shown verbatim, with its own provenance, confidence
and materiality. What this module adds is the fixed section structure, grouping, labels, a small
set of engine-owned sentences and cross-references by id.

**What it reads.** One genuine strict `SynthesisSet` (through `synthesis.grounding`), and,
optionally, one `StrategyResult` and any number of `DecisionResult`s bound to that same set
object, and one SWOT record accepted only when its own placements rebuild it exactly over that
set. KPI, anomaly, forecast, evidence and command objects are never direct inputs: they reach the
report only as statements and registered objects of the set.

**What it never does.** It writes no summary prose, no recommendation, no confidence of its own,
no score, rating, target or ranking. It re-judges no materiality, settles no conflict, drops no
limitation, reads no file, retrieves nothing, dispatches nothing, executes nothing and adds
nothing to the synthesis set.

**Lifecycle.** Every report this module builds is a `draft`, and there is no path here to
`final`: finalising is the M11 verifier's operation (ADR-0033 section 13).
"""

import copy
import hashlib
import json

from . import config as config_mod
from . import decision_support as decision_mod
from . import strategy as strategy_mod
from . import swot as swot_mod
from .kpi import catalog as kpi_catalog
from .quality import contract as quality_contract
from .synthesis import contract as contract_mod
from .synthesis import grounding
from .synthesis import limitations as limitations_mod
from .synthesis import research_footing as footing_mod
from .synthesis import synthesis_set as set_mod

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "executive_report"
#: The assembling capability. Not a class-7 issuer: it is absent from
#: `strategy.RECOMMENDATION_ISSUERS`, and nothing here builds a recommendation record.
ISSUED_BY = "bops-executive-report"
ISSUES_RECOMMENDATIONS = False
EXECUTES_ACTIONS = False
PRODUCES_FINAL = False

DRAFT = "draft"
FINAL = "final"
LIFECYCLES = (DRAFT, FINAL)
UNVERIFIED = "unverified"

LIFECYCLE_NOTE = (
    "Draft report. It has not been checked by the analysis verifier, which alone can move a "
    "draft to final, and it must be presented as unverified wherever it appears.")

HUMAN_DECISION = (
    "This is a draft report for people to read and decide on. BusinessOps assembled it from "
    "analysis already produced: it made no decision, recorded no approval and executes nothing. "
    "Acting on anything in it - a system write, a message, an export or an overwrite - needs a "
    "person's decision and explicit per-action approval, and financial transactions are "
    "prohibited.")

ORDER_NOTE = (
    "Sections appear in a fixed order. KPIs follow the KPI catalogue; statements follow the "
    "synthesis set; SWOT points, strategy recommendations and decision-package parts keep the "
    "order their own results give them; decision packages appear in the order they were "
    "supplied. No order here is a ranking, a priority or a preference.")

QUALITY_WARNING = (
    "The contributing data carries a data-quality WARNING. Read every figure below with that "
    "warning in mind.")

NO_DECISION_RECORDED = (
    "BusinessOps has recorded no decision and no approval. Every question below is open until a "
    "person decides it.")

# -- section names and statuses ------------------------------------------------

REPORTING_FRAME = "reporting_frame"
EXECUTIVE_SUMMARY = "executive_summary"
KPI_SCORECARD = "kpi_scorecard"
FINDINGS = "findings"
ANOMALIES = "anomalies"
OUTLOOK = "outlook"
SWOT = "swot"
STRATEGY_RECOMMENDATIONS = "strategy_recommendations"
DECISION_SUPPORT = "decision_support"
EVIDENCE_AND_UNCERTAINTY = "evidence_and_uncertainty"
DECISIONS_FOR_THE_READER = "decisions_for_the_reader"

#: The eleven sections, in the order ADR-0033 section 3 fixes.
SECTION_ORDER = (REPORTING_FRAME, EXECUTIVE_SUMMARY, KPI_SCORECARD, FINDINGS, ANOMALIES,
                 OUTLOOK, SWOT, STRATEGY_RECOMMENDATIONS, DECISION_SUPPORT,
                 EVIDENCE_AND_UNCERTAINTY, DECISIONS_FOR_THE_READER)

#: The sections whose status the executive summary reports (ADR-0033 section 4, item 7).
AVAILABILITY_SECTIONS = (KPI_SCORECARD, ANOMALIES, OUTLOOK, SWOT, STRATEGY_RECOMMENDATIONS,
                         DECISION_SUPPORT)

INCLUDED = "included"
EMPTY = "empty"
NOT_SUPPLIED = "not_supplied"
NOT_AVAILABLE = "not_available"
STATUSES = (INCLUDED, EMPTY, NOT_SUPPLIED, NOT_AVAILABLE)

#: Fixed reasons for a section with nothing to show. Chosen by rule, never written per report.
REASON_NO_KPI = "The synthesis set registered no KPI."
REASON_NO_FINDINGS = ("No statement outside the KPI, anomaly and forecast origins can be read as "
                      "evidence in this synthesis set.")
REASON_NO_ANOMALY = "The synthesis set holds no anomaly statement."
REASON_ANOMALY_NOT_READABLE = ("The synthesis set holds anomaly statements, but none can be read "
                               "as evidence; they are listed under evidence and uncertainty.")
REASON_NO_FORECAST = "No forecast statement in this synthesis set carries forecast provenance."
REASON_NO_SWOT = "No SWOT result was supplied."
REASON_EMPTY_SWOT = "The supplied SWOT places no point; each quadrant states its own empty state."
REASON_NO_STRATEGY = "No strategy result was supplied."
REASON_EMPTY_STRATEGY = ("The supplied strategy result issued no recommendation; its own empty "
                         "state applies.")
REASON_NO_DECISION = "No decision package was supplied."

NONE_MATERIAL = ("No statement in the synthesis set carries a material verdict that can be read "
                 "as evidence.")

#: The request a skill or command passes. Closed: any other field is refused.
REQUEST_FIELDS = ("reporting_period", "audience", "objective", "questions", "constraints")
TEXT_FIELDS = ("reporting_period", "audience", "objective")
LIST_FIELDS = ("questions", "constraints")

USER = "user"
EVIDENCE_LABEL = "evidence"
INTERPRETATION_LABEL = "interpretation"

_BUILD_TOKEN = object()


class ExecutiveReportError(contract_mod.SynthesisError):
    """An executive report or its input violates ADR-0033. Raised, never degraded."""


def _checked(call, *args, **kwargs):
    """Run a shared rule, reporting its refusal as this capability's error."""
    try:
        return call(*args, **kwargs)
    except (grounding.GroundingError, strategy_mod.StrategyError, swot_mod.SwotError,
            decision_mod.DecisionSupportError) as refusal:
        raise ExecutiveReportError(str(refusal))


def _sha256(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plain(value):
    """A value as the engine produced it, JSON-safe, never rounded here."""
    return None if value is None else str(value)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def _framing(request):
    """The closed framing request, stored verbatim as the user's words. Never evidence."""
    if not isinstance(request, dict):
        raise ExecutiveReportError(
            "the framing request is a record of %s; an empty record is valid"
            % ", ".join(REQUEST_FIELDS))
    extra = sorted(set(request) - set(REQUEST_FIELDS))
    if extra:
        raise ExecutiveReportError(
            "the framing request carries only %s; %s is not accepted. Confidence, trust, "
            "verification, lifecycle, targets and every other conclusion are derived or absent, "
            "and nothing in a report is scored, weighted, ranked or prioritised."
            % (", ".join(REQUEST_FIELDS), ", ".join(str(e) for e in extra)))
    framing = {}
    for name in TEXT_FIELDS:
        value = request.get(name)
        if value is None:
            framing[name] = {"text": None, "origin": None, "stated": False}
            continue
        if not isinstance(value, str) or not value.strip():
            raise ExecutiveReportError("%s, where given, is non-blank text" % name)
        framing[name] = {"text": value, "origin": USER, "stated": True}
    for name in LIST_FIELDS:
        values = request.get(name)
        if values is None:
            framing[name] = []
            continue
        if not isinstance(values, (list, tuple)) or not all(
                isinstance(v, str) and v.strip() for v in values):
            raise ExecutiveReportError("%s, where given, is a list of non-blank text" % name)
        if len(set(values)) != len(values):
            raise ExecutiveReportError("%s names the same text twice" % name)
        framing[name] = [{"text": value, "origin": USER} for value in values]
    return framing


def _strategy_input(synthesis, strategy_result):
    if strategy_result is None:
        return None
    if type(strategy_result) is not strategy_mod.StrategyResult:
        raise ExecutiveReportError(
            "a strategy input is the one StrategyResult strategy.build() produced; a serialised "
            "result, a list of results or a look-alike was never grounded")
    if not strategy_result.is_bound_to(synthesis):
        raise ExecutiveReportError(
            "the StrategyResult is not bound to this synthesis set - a different set, or the "
            "same set changed since - so its records cannot be assembled with it")
    return strategy_result


def _swot_placements(record):
    """The placements a SWOT record carries, or a refusal if it is not shaped like one."""
    if not isinstance(record, dict) or not isinstance(record.get("quadrants"), list):
        raise ExecutiveReportError(
            "a SWOT input is the record swot.build() returned, with its quadrants")
    placements = []
    for quadrant in record["quadrants"]:
        if not isinstance(quadrant, dict) or not isinstance(quadrant.get("points"), list):
            raise ExecutiveReportError("a SWOT quadrant carries a list of points")
        for point in quadrant["points"]:
            if not isinstance(point, dict):
                raise ExecutiveReportError("a SWOT point is a record")
            placements.append({"quadrant": point.get("quadrant"), "tag": point.get("tag"),
                               "synthesis_id": point.get("synthesis_id")})
    return placements


def _swot_digest(synthesis, record):
    """The SWOT record's digest, if its own placements rebuild it exactly over this set."""
    rebuilt = _checked(swot_mod.build, synthesis, _swot_placements(record))
    supplied = swot_mod.to_json(record)
    if swot_mod.to_json(rebuilt) != supplied:
        raise ExecutiveReportError(
            "the SWOT record is not what its own placements produce over this synthesis set - a "
            "different set, an edited record, or the set changed since - so it is not assembled")
    return _sha256(supplied)


def _swot_input(synthesis, swot):
    if swot is None:
        return None, None
    if isinstance(swot, (list, tuple)):
        raise ExecutiveReportError("a report assembles at most one SWOT result")
    return swot, _swot_digest(synthesis, swot)


def _decision_inputs(synthesis, decision_results, strategy_result):
    if decision_results is None:
        return []
    if not isinstance(decision_results, (list, tuple)):
        raise ExecutiveReportError(
            "decision packages are passed as a list of DecisionResult objects, in the order "
            "they are to appear")
    from . import verification as verification_mod          # a final package is M11's object
    accepted = (decision_mod.DecisionResult, verification_mod.FinalDecisionResult)
    packages, digests = [], set()
    for package in decision_results:
        if type(package) not in accepted:
            raise ExecutiveReportError(
                "a decision package is the DecisionResult decision_support.build() produced; a "
                "serialised package or a look-alike was never grounded")
        if not package.is_bound_to(synthesis):
            raise ExecutiveReportError(
                "a DecisionResult is not bound to this synthesis set - a different set, or the "
                "same set changed since - so it cannot be assembled with it")
        if strategy_result is not None and package.strategy_result is not None \
                and package.strategy_result is not strategy_result:
            raise ExecutiveReportError(
                "a decision package was built with a different StrategyResult from the one "
                "supplied; one report assembles one set of strategy records")
        digest = _sha256(package.to_json())
        if digest in digests or any(package is held for held, _d in packages):
            raise ExecutiveReportError(
                "the same decision package is supplied twice; one package is shown once")
        digests.add(digest)
        packages.append((package, digest))
    return packages


# ---------------------------------------------------------------------------
# Statement views
# ---------------------------------------------------------------------------

def _plain_detail(synthesis, item, reason):
    """A statement the report shows but may not rest anything on, with the reason why."""
    record = item.as_dict()
    return {
        "synthesis_id": item.id,
        "kind": item.kind,
        "evidence_class": item.evidence_class,
        "origin": item.origin,
        "domain": item.domain,
        "trust": item.trust,
        "statement": item.statement,
        "support": item.support,
        "confidence": item.confidence,
        "confidence_reasons": list((item.confidence_detail or {}).get("reasons") or []),
        "material": item.is_material,
        "materiality": record.get("materiality"),
        "conflict_refs": sorted(item.conflict_refs),
        "unresolved_dimensions": (footing_mod.dimension_report(item)[1]
                                  if item.dimension_provenance else {}),
        "caveats": list(item.caveats),
        "limitations": limitations_mod.as_dicts(item.limitations),
        "chain": synthesis.chain(item),
        "reason": reason,
    }


def _classify(synthesis):
    """Each statement once, in set order: `(position, item, readable_detail | None, reason)`."""
    synthesis = _checked(grounding.genuine_set, synthesis)
    index = grounding.index(synthesis)
    classified = []
    for position, item in enumerate(synthesis.items):
        _checked(grounding.one, index, item.id)
        if item.kind == contract_mod.ASSUMPTION:
            classified.append((position, item, None,
                               "An assumption is disclosed, never evidence."))
            continue
        try:
            grounding.evidence_domains(index, position, item)
        except grounding.GroundingError as refusal:
            classified.append((position, item, None, str(refusal)))
            continue
        detail = _checked(strategy_mod.statement_detail, synthesis, index, position, item)
        classified.append((position, item, detail, None))
    return synthesis, classified


def _label(item):
    return INTERPRETATION_LABEL if item.kind == contract_mod.INTERPRETATION else EVIDENCE_LABEL


def _entry(item, detail, **extra):
    """One readable statement: its grounded detail, with its caveats and limitations beside it."""
    entry = {"label": _label(item), "statement_detail": detail, "caveats": list(item.caveats),
             "limitations": limitations_mod.as_dicts(item.limitations)}
    entry.update(extra)
    return entry


def _section(status, reason=None, **content):
    record = {"status": status, "reason": reason}
    record.update(content)
    return record


def lifecycle_label(record):
    """`<lifecycle> — <verification>` exactly as a package record carries them. Reads, never sets."""
    return "%s — %s" % (record.get("lifecycle"), record.get("verification"))


def package_entry(record, digest):
    """One decision package for the report: the record whole, with its label beside it.

    A pure view. It copies the record and changes nothing in it, so a future `final` package
    (ADR-0032 section 13) is shown exactly as carried, with whatever lifecycle it states.
    """
    return {"package_digest": digest, "lifecycle_label": lifecycle_label(record),
            "package": copy.deepcopy(record)}


# ---------------------------------------------------------------------------
# The result
# ---------------------------------------------------------------------------

class ExecutiveReportResult:
    """A draft executive report assembled over one genuine strict synthesis set.

    Built only by `build()`. Holds the set object and its digest, and each component object with
    the digest of its serialisation at build time; `as_dict()` and `to_json()` refuse once the
    set changes, a component is no longer bound, or a component's digest no longer matches.
    """

    __slots__ = ("_synthesis", "_digest", "_strategy", "_strategy_digest", "_swot",
                 "_swot_digest", "_packages", "_framing", "_config_view", "_report", "_request",
                 "_config")

    def __init__(self, synthesis, digest, strategy, strategy_digest, swot, swot_digest,
                 packages, framing, config_view, report, request=None, config=None,
                 _token=None):
        if _token is not _BUILD_TOKEN:
            raise ExecutiveReportError(
                "an ExecutiveReportResult is built by executive_report.build() from a genuine "
                "synthesis set; a report assembled elsewhere was never bound to one")
        self._synthesis = synthesis
        self._digest = digest
        self._strategy = strategy
        self._strategy_digest = strategy_digest
        self._swot = swot
        self._swot_digest = swot_digest
        self._packages = packages
        self._framing = framing
        self._config_view = config_view
        self._report = report
        self._request = copy.deepcopy(request)
        self._config = config

    @property
    def synthesis(self):
        return self._synthesis

    @property
    def synthesis_digest(self):
        return self._digest

    @property
    def lifecycle(self):
        """Always `draft` in this milestone. There is no setter."""
        return DRAFT

    @property
    def report_id(self):
        return self._report["report_id"]

    # -- read-only views of what the report was assembled from (ADR-0034 section 5.2) --------

    @property
    def request(self):
        """A copy of the framing request as supplied."""
        return copy.deepcopy(self._request)

    @property
    def config(self):
        """The `ResolvedConfig` the report was built with, or `None`."""
        return self._config

    @property
    def strategy_result(self):
        return self._strategy

    @property
    def swot(self):
        """A copy of the SWOT record as supplied, or `None`."""
        return copy.deepcopy(self._swot)

    @property
    def decision_results(self):
        """The decision package objects, in supplied order."""
        return [package for package, _digest in self._packages]

    def is_bound_to(self, synthesis):
        """Whether the set and every component are exactly as they were when assembled."""
        if synthesis is not self._synthesis \
                or strategy_mod.synthesis_digest(synthesis) != self._digest:
            return False
        try:
            if self._strategy is not None and (
                    not self._strategy.is_bound_to(synthesis)
                    or _sha256(self._strategy.to_json()) != self._strategy_digest):
                return False
            for package, digest in self._packages:
                if not package.is_bound_to(synthesis) or _sha256(package.to_json()) != digest:
                    return False
            if self._swot is not None and _swot_digest(synthesis, self._swot) \
                    != self._swot_digest:
                return False
        except (ExecutiveReportError, contract_mod.SynthesisError):
            return False
        return True

    def _require_bound(self):
        if not self.is_bound_to(self._synthesis):
            raise ExecutiveReportError(
                "the synthesis set or an assembled result changed after this report was built; "
                "build it again rather than carrying its content onto different material")

    def as_dict(self):
        self._require_bound()
        return copy.deepcopy(self._report)

    def to_json(self, indent=None):
        """Deterministic serialisation. Key order is the contract's, so keys are not sorted."""
        return json.dumps(self.as_dict(), indent=indent, default=str)

    def __repr__(self):
        return "ExecutiveReportResult(draft, %s)" % self._report["report_id"]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(synthesis, request, strategy_result=None, swot=None, decision_results=None,
          config=None):
    """Assemble a draft executive report, or raise `ExecutiveReportError` and emit nothing.

    `request` is the closed framing record (`REQUEST_FIELDS`, each optional). `strategy_result`
    is at most one bound `StrategyResult`; `swot` at most one SWOT record; `decision_results` a
    list of bound `DecisionResult`s in presentation order; `config` an optional `ResolvedConfig`
    read only to state which materiality thresholds applied and their layer.
    """
    synthesis, classified = _classify(synthesis)
    if synthesis.quality_grade == quality_contract.CRITICAL:
        raise ExecutiveReportError(
            "the synthesis set is declared CRITICAL quality. A critical grade halts analysis, "
            "and a report over it would present figures the data cannot support.")
    framing = _framing(request)
    strategy_result = _strategy_input(synthesis, strategy_result)
    swot, swot_digest = _swot_input(synthesis, swot)
    packages = _decision_inputs(synthesis, decision_results, strategy_result)
    if config is not None and type(config) is not config_mod.ResolvedConfig:
        raise ExecutiveReportError(
            "configuration is the ResolvedConfig the precedence chain produced; thresholds are "
            "never typed in by the caller")

    digest = strategy_mod.synthesis_digest(synthesis)
    strategy_record = strategy_result.as_dict() if strategy_result is not None else None
    strategy_digest = (_sha256(strategy_result.to_json())
                       if strategy_result is not None else None)
    package_records = [(package.as_dict(), package_digest)
                       for package, package_digest in packages]

    thresholds = []
    if config is not None:
        for key in decision_mod.MATERIALITY_KEYS:
            dotted = "materiality.%s" % key
            value = config.get(dotted)
            if value is not None:
                thresholds.append({"key": dotted, "value": _plain(value),
                                   "source": "%s layer" % config.source_of(dotted)})

    readable = [(p, item, detail) for p, item, detail, _r in classified if detail is not None]
    unreadable = [(p, item, reason) for p, item, detail, reason in classified if detail is None]

    sections = {
        REPORTING_FRAME: _reporting_frame(synthesis, framing, thresholds),
        KPI_SCORECARD: _kpi_scorecard(synthesis, readable),
        FINDINGS: _findings(readable),
        ANOMALIES: _anomalies(synthesis, classified, readable),
        OUTLOOK: _section(NOT_AVAILABLE, REASON_NO_FORECAST, statements=[]),
        SWOT: _swot_section(swot),
        STRATEGY_RECOMMENDATIONS: _strategy_section(strategy_record),
        DECISION_SUPPORT: _decision_section(package_records),
        EVIDENCE_AND_UNCERTAINTY: _evidence_and_uncertainty(synthesis, unreadable, readable,
                                                            strategy_record, package_records),
        DECISIONS_FOR_THE_READER: _decisions_for_the_reader(strategy_record, package_records),
    }
    # The summary reports the other sections' availability, so it is assembled after them.
    sections[EXECUTIVE_SUMMARY] = _executive_summary(synthesis, classified, strategy_record,
                                                     package_records, sections)

    identity = json.dumps({"synthesis_digest": digest, "strategy": strategy_digest,
                           "swot": swot_digest,
                           "packages": [d for _r, d in package_records],
                           "framing": framing}, sort_keys=True, default=str)
    report = {
        "schema_version": SCHEMA_VERSION,
        "analysis": ANALYSIS,
        "issued_by": ISSUED_BY,
        "report_id": "rpt-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12],
        "lifecycle": DRAFT,
        "verification": UNVERIFIED,
        "lifecycle_note": LIFECYCLE_NOTE,
        "subject": synthesis.subject,
        "as_of": synthesis.as_of,
        "business_model": synthesis.business_model,
        "currency": synthesis.currency,
        "quality_grade": synthesis.quality_grade,
        "synthesis_digest": digest,
        "sources": {
            "strategy": {"included": strategy_record is not None, "digest": strategy_digest,
                         "synthesis_digest": (strategy_record or {}).get("synthesis_digest"),
                         "recommendation_ids": [r["recommendation_id"] for r in
                                                (strategy_record or {}).get(
                                                    "recommendations", [])]},
            "swot": {"included": swot is not None, "digest": swot_digest},
            "decision_packages": [{"digest": package_digest,
                                   "lifecycle": record["lifecycle"],
                                   "verification": record["verification"],
                                   "synthesis_digest": record["synthesis_digest"],
                                   "decision_question":
                                       record["body"]["decision_question"]["text"]}
                                  for record, package_digest in package_records],
        },
        "trust_statement": set_mod.TRUST_STATEMENT,
        "human_decision": HUMAN_DECISION,
        "order_note": ORDER_NOTE,
        "section_order": list(SECTION_ORDER),
        "sections": dict((name, sections[name]) for name in SECTION_ORDER),
    }

    if strategy_mod.synthesis_digest(synthesis) != digest:
        raise ExecutiveReportError("the synthesis set changed while the report was assembled")
    return ExecutiveReportResult(synthesis, digest, strategy_result, strategy_digest, swot,
                                 swot_digest, packages, framing, thresholds, report,
                                 request=request, config=config, _token=_BUILD_TOKEN)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _reporting_frame(synthesis, framing, thresholds):
    warning = synthesis.quality_grade == quality_contract.WARNING
    return _section(
        INCLUDED,
        lifecycle=DRAFT, verification=UNVERIFIED, lifecycle_note=LIFECYCLE_NOTE,
        quality_grade=synthesis.quality_grade,
        quality_warning=QUALITY_WARNING if warning else None,
        subject=synthesis.subject, business_model=synthesis.business_model,
        currency=synthesis.currency, as_of=synthesis.as_of,
        framing=copy.deepcopy(framing),
        datasets=synthesis.registered_datasets(),
        external_evidence=synthesis.registered_evidence_sets(),
        materiality_thresholds=thresholds)


def _executive_summary(synthesis, classified, strategy_record, package_records, sections):
    material = [_entry(item, detail)
                for _p, item, detail, _r in classified
                if detail is not None and item.is_material]
    material_not_supported = [item.id for _p, item, detail, _r in classified
                              if detail is None and item.is_material
                              and item.kind != contract_mod.ASSUMPTION]
    not_assessed = len([item for _p, item, _d, _r in classified if not item.materiality])
    recommendations = [{"recommendation_id": record["recommendation_id"],
                        "issued_by": record["issued_by"], "action": record["action"],
                        "confidence": record["confidence"]}
                       for record in (strategy_record or {}).get("recommendations", [])]
    set_confidence = synthesis.confidence().as_dict()
    return _section(
        INCLUDED,
        material_statements=material,
        material_statements_note=None if material else NONE_MATERIAL,
        material_not_supported=material_not_supported,
        materiality_not_assessed=not_assessed,
        recommendations=recommendations,
        decisions=[_decision_view(record, digest) for record, digest in package_records],
        synthesis_confidence=set_confidence,
        conflict_count=len(synthesis.conflicts),
        limitation_count=len(synthesis.limitations),
        availability=[{"section": name, "status": sections[name]["status"]}
                      for name in AVAILABILITY_SECTIONS])


def _decision_view(record, digest):
    guidance = record["body"]["guidance"]
    labels = dict((o["option_id"], o["label"]) for o in record["body"]["options"])
    preferred = guidance["preferred_option"]
    return {"package_digest": digest,
            "decision_question": record["body"]["decision_question"]["text"],
            "lifecycle": record["lifecycle"], "verification": record["verification"],
            "lifecycle_label": lifecycle_label(record),
            "preferred_option": ({"option_id": preferred, "label": labels[preferred]}
                                 if preferred else None),
            "preference_basis": copy.deepcopy(guidance["preference_basis"]),
            "no_preference_reason": guidance["no_preference_reason"]}


def _kpi_scorecard(synthesis, readable):
    registered = dict((result.kpi_id, result) for result in synthesis.registered_kpis())
    if not registered:
        return _section(NOT_AVAILABLE, REASON_NO_KPI, rows=[])
    order = [definition.kpi_id for definition in kpi_catalog.CATALOGUE]
    ordered = [kpi_id for kpi_id in order if kpi_id in registered] + sorted(
        kpi_id for kpi_id in registered if kpi_id not in order)
    rows = []
    for kpi_id in ordered:
        result = registered[kpi_id]
        statements = []
        for _p, item, detail in readable:
            if item.origin == contract_mod.ORIGIN_KPI and any(
                    ref.kind == contract_mod.P_KPI and str(ref.ref_id) == kpi_id
                    for ref in item.provenance):
                statements.append(_entry(item, detail, prior=_plain(item.comparison),
                                         change=_plain(item.change),
                                         change_pct=_plain(item.change_pct)))
        value_bearing = result.available
        rows.append({
            "kpi_id": kpi_id,
            "name": result.definition.name,
            "status": result.status,
            "value": _plain(result.value) if value_bearing else None,
            "unit": result.unit,
            "currency": result.currency,
            "periods": _plain(result.periods),
            "reason": None if value_bearing else result.reason,
            "caveats": [str(c) for c in result.caveats],
            "basis": getattr(result.definition, "formula", None) or kpi_id,
            "statements": statements,
        })
    return _section(INCLUDED, rows=rows)


def _findings(readable):
    held = (contract_mod.ORIGIN_KPI, contract_mod.ORIGIN_ANOMALY, contract_mod.ORIGIN_FORECAST)
    evidence = [_entry(item, detail) for _p, item, detail in readable
                if item.origin not in held and item.kind != contract_mod.INTERPRETATION]
    interpretations = [_entry(item, detail) for _p, item, detail in readable
                       if item.origin not in held and item.kind == contract_mod.INTERPRETATION]
    if not evidence and not interpretations:
        return _section(EMPTY, REASON_NO_FINDINGS, evidence=[], interpretations=[])
    return _section(INCLUDED, evidence=evidence, interpretations=interpretations)


def _anomalies(synthesis, classified, readable):
    present = [item for _p, item, _d, _r in classified
               if item.origin == contract_mod.ORIGIN_ANOMALY]
    if not present:
        return _section(NOT_AVAILABLE, REASON_NO_ANOMALY, statements=[])
    statements = []
    for _p, item, detail in readable:
        if item.origin != contract_mod.ORIGIN_ANOMALY:
            continue
        anomaly = None
        for ref in item.provenance:
            if ref.kind == contract_mod.P_ANOMALY:
                finding = synthesis.resolve_ref(ref)
                if finding is not None:
                    # The finding's own values, as the anomaly engine computed them; the
                    # baseline is its `comparison` and the deviation its `change`.
                    anomaly = {"analysis_id": str(ref.ref_id), "metric": finding.metric,
                               "period": _plain(finding.period),
                               "observed": _plain(finding.observed),
                               "baseline": _plain(finding.comparison),
                               "deviation": _plain(finding.change),
                               "deviation_pct": _plain(finding.change_pct),
                               "unit": finding.unit, "currency": finding.currency,
                               "dimension": finding.dimension,
                               "dimension_value": _plain(finding.dimension_value),
                               "dimension_redacted": bool(finding.dimension_redacted),
                               "basis": finding.basis}
                    break
        statements.append(_entry(item, detail, anomaly=anomaly))
    if not statements:
        return _section(EMPTY, REASON_ANOMALY_NOT_READABLE, statements=[])
    return _section(INCLUDED, statements=statements)


def _swot_section(swot):
    if swot is None:
        return _section(NOT_SUPPLIED, REASON_NO_SWOT, result=None)
    placed = any(quadrant["points"] for quadrant in swot["quadrants"])
    return _section(INCLUDED if placed else EMPTY, None if placed else REASON_EMPTY_SWOT,
                    result=copy.deepcopy(swot))


def _strategy_section(record):
    if record is None:
        return _section(NOT_SUPPLIED, REASON_NO_STRATEGY, result=None)
    issued = bool(record["recommendations"])
    return _section(INCLUDED if issued else EMPTY, None if issued else REASON_EMPTY_STRATEGY,
                    result=record)


def _decision_section(package_records):
    if not package_records:
        return _section(NOT_SUPPLIED, REASON_NO_DECISION, packages=[])
    return _section(INCLUDED, packages=[package_entry(record, digest)
                                        for record, digest in package_records])


def _evidence_and_uncertainty(synthesis, unreadable, readable, strategy_record,
                              package_records):
    assumptions = [_plain_detail(synthesis, item, reason) for _p, item, reason in unreadable
                   if item.kind == contract_mod.ASSUMPTION]
    not_supported = [_plain_detail(synthesis, item, reason) for _p, item, reason in unreadable
                     if item.kind != contract_mod.ASSUMPTION]
    unresolved = []
    for _p, item, detail in readable:
        for dimension, reason in sorted(detail["unresolved_dimensions"].items()):
            unresolved.append({"synthesis_id": item.id, "dimension": dimension,
                               "reason": reason})
    components = []
    if strategy_record is not None:
        components.append({"component": "strategy_recommendations",
                           "confidence": copy.deepcopy(strategy_record["confidence"])})
    for record, digest in package_records:
        uncertainty = record["body"]["uncertainty"]
        components.append({"component": "decision_package", "package_digest": digest,
                           "lifecycle_label": lifecycle_label(record),
                           "confidence": {"confidence": uncertainty["confidence"],
                                          "reasons": list(uncertainty["confidence_reasons"])}})
    return _section(
        INCLUDED,
        synthesis_confidence=synthesis.confidence().as_dict(),
        component_confidence=components,
        conflicts=[conflict.as_dict() for conflict in synthesis.conflicts],
        limitations=limitations_mod.as_dicts(synthesis.limitations),
        assumptions=assumptions,
        not_supported=not_supported,
        unresolved_dimensions=unresolved)


def _decisions_for_the_reader(strategy_record, package_records):
    questions, next_steps = [], []
    for record, digest in package_records:
        questions.append(_decision_view(record, digest))
        for position, step in enumerate(record["body"]["uncertainty"]["next_steps"]):
            next_steps.append({"package_digest": digest, "index": position,
                               "text": step["text"],
                               "addresses": copy.deepcopy(step["addresses"])})
    return _section(
        INCLUDED,
        human_decision=HUMAN_DECISION,
        no_decision_recorded=NO_DECISION_RECORDED,
        decision_questions=questions,
        recommendations_awaiting_decision=[
            r["recommendation_id"] for r in (strategy_record or {}).get("recommendations", [])],
        next_steps=next_steps)


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

_TITLES = {REPORTING_FRAME: "Reporting frame", EXECUTIVE_SUMMARY: "Executive summary",
           KPI_SCORECARD: "KPI scorecard", FINDINGS: "Findings", ANOMALIES: "Anomalies",
           OUTLOOK: "Outlook", SWOT: "SWOT", STRATEGY_RECOMMENDATIONS: "Strategy recommendations",
           DECISION_SUPPORT: "Decision support",
           EVIDENCE_AND_UNCERTAINTY: "Evidence, confidence and limitations",
           DECISIONS_FOR_THE_READER: "Decisions for the reader"}


def _reasons(entry):
    reasons = entry.get("confidence_reasons") or entry.get("reasons") or []
    return " — %s" % ", ".join(reasons) if reasons else ""


def _statement_line(detail, label=None):
    materiality = (detail.get("materiality") or {}).get("outcome") or "not assessed"
    return "- `%s` [%s%s · %s · %s · %s%s · materiality %s] %s" % (
        detail["synthesis_id"], label + " · " if label else "", detail["kind"], detail["domain"],
        detail["support"], detail["confidence"], _reasons(detail), materiality,
        detail["statement"])


def render(result):
    """The report as markdown, formatted once. Adds no sentence of analysis."""
    record = result.as_dict() if isinstance(result, ExecutiveReportResult) else result
    sections = record["sections"]
    lines = ["# Executive report — %s" % (record.get("subject") or "subject not stated"), "",
             "**Lifecycle:** %s — %s" % (record["lifecycle"], record["verification"]),
             "_%s_" % record["lifecycle_note"], ""]
    frame = sections[REPORTING_FRAME]
    if frame["quality_warning"]:
        lines += ["> **Data quality:** %s" % frame["quality_warning"], ""]
    lines += ["> %s" % record["human_decision"], "", "_%s_" % record["order_note"], ""]

    for number, name in enumerate(record["section_order"], start=1):
        section = sections[name]
        lines += ["## %d. %s" % (number, _TITLES[name]), ""]
        if section["status"] != INCLUDED:
            lines.append("_%s — %s_" % (section["status"].replace("_", " "), section["reason"]))
            if name not in (SWOT, STRATEGY_RECOMMENDATIONS):
                lines.append("")
                continue
        if name == REPORTING_FRAME:
            lines.append("Report `%s` · synthesis `%s`" % (record["report_id"],
                                                          record["synthesis_digest"]))
            lines.append("Subject: %s · Business model: %s · Currency: %s · As of: %s · "
                         "Quality grade: %s" % tuple(section[k] or "not stated" for k in (
                             "subject", "business_model", "currency", "as_of",
                             "quality_grade")))
            for key in TEXT_FIELDS:
                entry = section["framing"][key]
                lines.append("- %s _(user)_: %s" % (key.replace("_", " ").capitalize(),
                                                    entry["text"]) if entry["stated"]
                             else "- %s: _not stated_" % key.replace("_", " ").capitalize())
            for key in LIST_FIELDS:
                lines += ["- %s _(user)_: %s" % (key[:-1].capitalize(), e["text"])
                          for e in section["framing"][key]]
            lines += ["- Dataset `%s` (%s)" % (d["id"], d.get("label") or "unlabelled")
                      for d in section["datasets"]]
            lines += ["- External research: %s (%s)" % (e["subject"], e["category"])
                      for e in section["external_evidence"]]
            lines += ["- Threshold %s = %s (%s)" % (t["key"], t["value"], t["source"])
                      for t in section["materiality_thresholds"]]
        elif name == EXECUTIVE_SUMMARY:
            if section["material_statements_note"]:
                lines.append("_%s_" % section["material_statements_note"])
            lines += [_statement_line(e["statement_detail"], e["label"])
                      for e in section["material_statements"]]
            if section["material_not_supported"]:
                lines.append("- Material but not supported (see section 10): %s" % ", ".join(
                    "`%s`" % i for i in section["material_not_supported"]))
            lines.append("- Statements with no materiality verdict: %d"
                         % section["materiality_not_assessed"])
            lines += ["- Recommendation `%s` _(%s)_: %s — confidence %s" % (
                r["recommendation_id"], r["issued_by"], r["action"], r["confidence"])
                for r in section["recommendations"]]
            for d in section["decisions"]:
                lines.append("- Decision _(%s)_: %s — %s" % (
                    d["lifecycle_label"], d["decision_question"],
                    "preferred option: %s" % d["preferred_option"]["label"]
                    if d["preferred_option"] else d["no_preference_reason"]))
            lines.append("- Synthesis set confidence: %s%s · %d conflicts · %d limitations" % (
                section["synthesis_confidence"]["confidence"],
                _reasons(section["synthesis_confidence"]), section["conflict_count"],
                section["limitation_count"]))
            lines.append("- Availability: %s" % " · ".join(
                "%s %s" % (_TITLES[a["section"]], a["status"].replace("_", " "))
                for a in section["availability"]))
        elif name == KPI_SCORECARD:
            lines += ["| KPI | Status | Value | Prior | Change | Change % | Materiality | "
                      "Confidence |", "|---|---|---|---|---|---|---|---|"]
            for row in section["rows"]:
                statement = row["statements"][0] if row["statements"] else None
                detail = statement["statement_detail"] if statement else {}
                lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    row["name"], row["status"], row["value"] or "—",
                    (statement or {}).get("prior") or "not computed",
                    (statement or {}).get("change") or "not computed",
                    (statement or {}).get("change_pct") or "not computed",
                    ((detail.get("materiality") or {}).get("outcome") or "not assessed")
                    if statement else "—",
                    detail.get("confidence") or "—"))
            lines += ["- _%s — %s:_ %s" % (row["name"], row["status"], row["reason"])
                      for row in section["rows"] if row["reason"]]
        elif name == FINDINGS:
            lines += [_statement_line(e["statement_detail"], e["label"])
                      for e in section["evidence"]]
            lines += [_statement_line(e["statement_detail"], e["label"])
                      for e in section["interpretations"]]
        elif name == ANOMALIES:
            for entry in section["statements"]:
                lines.append(_statement_line(entry["statement_detail"]))
                lines += ["  - _%s_" % caveat for caveat in entry["caveats"]]
        elif name == SWOT and section["result"]:
            lines.append(swot_mod.render(section["result"]))
        elif name == STRATEGY_RECOMMENDATIONS and section["result"]:
            lines.append(strategy_mod.render(section["result"]))
        elif name == DECISION_SUPPORT:
            for entry in section["packages"]:
                lines += ["**Package `%s` — %s**" % (entry["package_digest"],
                                                     entry["lifecycle_label"]), "",
                          decision_mod.render(entry["package"])]
        elif name == EVIDENCE_AND_UNCERTAINTY:
            lines.append("**Synthesis set confidence:** %s%s" % (
                section["synthesis_confidence"]["confidence"],
                _reasons(section["synthesis_confidence"])))
            for c in section["component_confidence"]:
                lines.append("- %s confidence%s: %s%s" % (
                    c["component"].replace("_", " "),
                    " (%s)" % c["lifecycle_label"] if c.get("lifecycle_label") else "",
                    c["confidence"]["confidence"], _reasons(c["confidence"])))
            lines += ["- Conflict `%s`: %s" % (c["conflict_id"], c.get("reason") or "")
                      for c in section["conflicts"]]
            lines += ["- Limitation `%s` %s — %s" % (l["code"], l.get("subject") or "",
                                                     l.get("reason") or "")
                      for l in section["limitations"]]
            lines += ["- Assumption `%s`: %s _(disclosed, never evidence)_" % (
                a["synthesis_id"], a["statement"]) for a in section["assumptions"]]
            lines += ["- Not supported `%s`: %s _(%s)_" % (s["synthesis_id"], s["statement"],
                                                          s["reason"])
                      for s in section["not_supported"]]
            lines += ["- Unresolved `%s` %s (%s)" % (u["synthesis_id"], u["dimension"],
                                                     u["reason"])
                      for u in section["unresolved_dimensions"]]
        elif name == DECISIONS_FOR_THE_READER:
            lines += ["> %s" % section["human_decision"], "",
                      "_%s_" % section["no_decision_recorded"]]
            for d in section["decision_questions"]:
                lines.append("- %s _(%s)_ — %s" % (
                    d["decision_question"], d["lifecycle_label"],
                    "preferred option: %s" % d["preferred_option"]["label"]
                    if d["preferred_option"] else d["no_preference_reason"]))
            if section["recommendations_awaiting_decision"]:
                lines.append("- Recommendations awaiting a person's decision: %s" % ", ".join(
                    "`%s`" % i for i in section["recommendations_awaiting_decision"]))
            lines += ["- Evidence gap (package `%s`, step %d): %s" % (
                s["package_digest"], s["index"], s["text"]) for s in section["next_steps"]]
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "build", "render", "package_entry", "lifecycle_label", "ExecutiveReportResult",
    "ExecutiveReportError", "SCHEMA_VERSION", "ANALYSIS", "ISSUED_BY", "ISSUES_RECOMMENDATIONS",
    "EXECUTES_ACTIONS", "PRODUCES_FINAL", "DRAFT", "FINAL", "LIFECYCLES", "UNVERIFIED",
    "LIFECYCLE_NOTE", "HUMAN_DECISION", "ORDER_NOTE", "QUALITY_WARNING", "NO_DECISION_RECORDED",
    "SECTION_ORDER", "STATUSES", "INCLUDED", "EMPTY", "NOT_SUPPLIED", "NOT_AVAILABLE",
    "REQUEST_FIELDS", "REASON_NO_FORECAST",
]
