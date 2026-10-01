"""Command execution: sequence what already exists, and record what happened.

A command run is four steps and no arithmetic:

  1. resolve the command's declaration from the registry;
  2. run the pipeline (ingestion → normalization → mapping → quality gate → KPIs);
  3. run the analytical domains the declaration names;
  4. for `/ask-business-data`, route the question and read the answer out of those results.

Nothing here computes a figure, applies a threshold, or classifies a field. Every number a
command reports was produced by the Milestone 5 engine or the Milestone 6 analytics before
this module saw it.

An unreadable source is returned as a structured result rather than raised, because a
command is a user-facing boundary and a traceback is not an answer. The error type is
recorded so the failure is still explicit.
"""

import datetime
import hashlib
import json
import os

from .. import pipeline as pipeline_mod
from ..analytics import presentation as presentation_mod
from ..errors import BusinessOpsError
from . import query as query_mod
from . import registry as registry_mod

OK = "ok"
HALTED = "halted"
UNAVAILABLE = "unavailable"
CLARIFICATION_NEEDED = "clarification_needed"
UNSUPPORTED = "unsupported"

#: How much of a command's declared metric set the data actually supported.
COMPLETE = "complete"
PARTIAL = "partial"
NONE_AVAILABLE = "unavailable"
NOT_APPLICABLE = "not_applicable"


class CommandResult:
    """One command run: the declaration, the underlying results, and the outcome."""

    __slots__ = ("command_id", "spec", "source", "question", "presentation", "result",
                 "analyses", "routing", "answer", "status", "reason", "error_type",
                 "started_at", "source_path", "source_sha256", "run_arguments",
                 "config_digest", "run_id")

    def __init__(self, spec, source=None, question=None,
                 presentation=presentation_mod.LOCAL, result=None, analyses=None,
                 routing=None, answer=None, status=OK, reason=None, error_type=None):
        self.command_id = spec.command_id
        self.spec = spec
        self.source = source
        self.question = question
        self.presentation = presentation
        self.result = result
        self.analyses = dict(analyses or {})
        self.routing = routing
        self.answer = answer
        self.status = status
        self.reason = reason
        self.error_type = error_type
        self.started_at = datetime.datetime.now().replace(microsecond=0).isoformat()
        #: The recomputation basis (ADR-0035 section 2). Set only on a run whose source bytes
        #: were identical before and after the pipeline read them; otherwise all `None`.
        self.source_path = None
        self.source_sha256 = None
        self.run_arguments = None
        self.config_digest = None
        self.run_id = None

    # -- pass-through accessors; the command layer stores no state of its own --

    @property
    def halted(self):
        return bool(self.result is not None and self.result.halted)

    @property
    def quality(self):
        return self.result.quality if self.result is not None else None

    @property
    def quality_grade(self):
        return self.quality.grade if self.quality is not None else None

    @property
    def kpis(self):
        return self.result.kpis if self.result is not None else {}

    @property
    def context(self):
        return self.result.context if self.result is not None else None

    @property
    def config(self):
        return self.result.config if self.result is not None else None

    @property
    def semantic_map(self):
        return self.result.semantic_map if self.result is not None else None

    @property
    def ledger(self):
        return self.result.ledger if self.result is not None else None

    @property
    def currency(self):
        for analysis in self.analyses.values():
            if analysis.currency:
                return analysis.currency
        if self.context is not None and self.context.get("reporting.currency"):
            return self.context.get("reporting.currency")
        if self.config is not None:
            return self.config.get("locale.currency", "USD")
        return None

    # -- aggregate views ----------------------------------------------------

    @property
    def analysis_keys(self):
        """Where this command's results live in `analyses`.

        An analytics command declares its domains; a forecast or anomaly command produces
        exactly one set, filed under its engine name. Reading the keys from the spec keeps
        every aggregate view below identical across all three.
        """
        if self.spec.engine != registry_mod.ANALYTICS_ENGINE:
            return (self.spec.engine,)
        return self.spec.domains

    @property
    def forecast_set(self):
        return self.analyses.get(registry_mod.FORECAST_ENGINE)

    @property
    def anomaly_set(self):
        return self.analyses.get(registry_mod.ANOMALY_ENGINE)

    def findings(self):
        """Every analytical finding this command produced, in declared order."""
        out = []
        for name in self.analysis_keys:
            analysis = self.analyses.get(name)
            if analysis is not None:
                out.extend(analysis.findings)
        return out

    def material_findings(self):
        from .. import materiality as materiality_mod
        return [f for f in self.findings()
                if f.materiality == materiality_mod.MATERIAL]

    def limitations(self):
        out = []
        for name in self.analysis_keys:
            analysis = self.analyses.get(name)
            if analysis is not None:
                out.extend((name, item) for item in analysis.limitations)
        return out

    def focus_kpis(self):
        """The metrics this command foregrounds, in declared order, present or not."""
        return [(kpi_id, self.kpis.get(kpi_id)) for kpi_id in self.spec.kpi_focus]

    def focus_coverage(self):
        """How much of the declared metric set the data supported.

        A command whose whole subject is absent must say so plainly. `/cash-flow-analysis`
        on a sales extract produces none of its five metrics, and reporting that as an
        ordinary run with some profitability context alongside would leave a reader to
        infer that cash was fine.
        """
        focus = self.focus_kpis()
        if not focus:
            return {"status": None, "available": 0, "total": 0,
                    "missing": [], "not_applicable": []}
        available, missing, not_applicable = [], [], []
        for kpi_id, result in focus:
            if result is not None and result.available:
                available.append(kpi_id)
            elif result is not None and result.status == "not_applicable":
                not_applicable.append(kpi_id)
            else:
                missing.append(kpi_id)
        if len(available) == len(focus):
            status = COMPLETE
        elif available:
            status = PARTIAL
        elif not_applicable and not missing:
            status = NOT_APPLICABLE
        else:
            status = NONE_AVAILABLE
        return {"status": status, "available": len(available), "total": len(focus),
                "missing": missing, "not_applicable": not_applicable}

    def summary(self):
        return {
            "command": "/%s" % self.command_id,
            "status": self.status,
            "quality_grade": self.quality_grade,
            "findings": len(self.findings()),
            "limitations": len(self.limitations()),
            "material": len(self.material_findings()),
            "focus_coverage": self.focus_coverage(),
            "domains": {name: analysis.status
                        for name, analysis in sorted(self.analyses.items())},
        }

    def as_dict(self):
        record = {
            "command": "/%s" % self.command_id,
            "status": self.status,
            "reason": self.reason,
            "error_type": self.error_type,
            "source": self.source,
            "question": self.question,
            "presentation": self.presentation,
            "spec": self.spec.as_dict(),
            "summary": self.summary(),
            "analyses": {name: analysis.as_dict()
                         for name, analysis in sorted(self.analyses.items())},
        }
        if self.result is not None:
            record["quality"] = (self.result.quality.as_dict()
                                 if self.result.quality else None)
            record["kpis"] = {k: v.as_dict() for k, v in sorted(self.kpis.items())}
        if self.routing is not None:
            record["routing"] = self.routing.as_dict()
        if self.answer is not None:
            record["answer"] = self.answer.as_dict()
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "CommandResult(/%s: %s)" % (self.command_id, self.status)


def _domains_for(spec, routing):
    """Which analytical domains this run needs.

    Everything except `/ask-business-data` declares its domains. A question routed to a
    metric needs none — the KPI engine has already produced it — so nothing is run that the
    answer does not use.
    """
    if spec.domains:
        return spec.domains
    if routing is not None and routing.routed and routing.domain and (
            routing.concept_kind == query_mod.DIMENSION):
        return (routing.domain,)
    return ()


#: Arguments that steer an engine rather than the pipeline, so they are separated before
#: `pipeline.run` is called rather than leaking into the reader as unknown keywords.
ENGINE_ARGS = ("horizon", "targets", "method", "metrics", "sensitivity")

SOURCE_CHANGED = (
    "The source file changed while it was being analysed, so nothing from this run is "
    "used. Run the command again on a file that is not being modified.")


def source_sha256(path):
    """SHA-256 of a file's complete bytes, as `sha256:<hex>`, or `None` if unreadable."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 16), b""):
                digest.update(block)
    except (OSError, IOError):
        return None
    return "sha256:" + digest.hexdigest()


def canonical_json(value):
    """The one canonical JSON form a recomputation basis is hashed over."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=str)


def run_identity(command_id, source_path, source_digest, run_arguments, config_digest):
    """`run-` + 12 hex, content-addressed over the whole recomputation basis (ADR-0035)."""
    seed = canonical_json({"command_id": command_id, "source_path": source_path,
                           "source_sha256": source_digest, "run_arguments": run_arguments,
                           "config_digest": config_digest})
    return "run-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _record_basis(command_result, source_path, before, run_arguments):
    """Attach the recomputation basis to a completed run. Computes no figure."""
    config = command_result.config
    if config is None:
        return
    config_digest = "sha256:" + hashlib.sha256(
        canonical_json(config.as_dict()).encode("utf-8")).hexdigest()
    command_result.source_path = source_path
    command_result.source_sha256 = before
    command_result.run_arguments = run_arguments
    command_result.config_digest = config_digest
    command_result.run_id = run_identity(command_result.command_id, source_path, before,
                                         run_arguments, config_digest)


def run(command_id, source=None, question=None,
        presentation=presentation_mod.LOCAL, **pipeline_kwargs):
    """Execute one command. Returns a `CommandResult`, never raises for bad input data."""
    spec = registry_mod.require(command_id)
    # Every argument except the source can change a figure or a statement, so all of them
    # are part of the run's identity (ADR-0035 section 2).
    run_arguments = json.loads(canonical_json(
        dict(pipeline_kwargs, question=question, presentation=presentation)))
    engine_args = {name: pipeline_kwargs.pop(name)
                   for name in ENGINE_ARGS if name in pipeline_kwargs}

    routing = None
    if spec.command_id == "ask-business-data":
        routing = query_mod.route(question)
        if routing.status == query_mod.UNSUPPORTED:
            return CommandResult(spec, source=source, question=question,
                                 presentation=presentation, routing=routing,
                                 answer=query_mod.Answer(routing, query_mod.UNSUPPORTED,
                                                         reason=routing.reason),
                                 status=UNSUPPORTED, reason=routing.reason)
        if routing.status == query_mod.CLARIFICATION_NEEDED:
            return CommandResult(spec, source=source, question=question,
                                 presentation=presentation, routing=routing,
                                 answer=query_mod.Answer(routing,
                                                         query_mod.CLARIFICATION_NEEDED,
                                                         reason=routing.reason),
                                 status=CLARIFICATION_NEEDED, reason=routing.reason)

    if not source:
        return CommandResult(spec, source=source, question=question,
                             presentation=presentation, routing=routing,
                             status=UNAVAILABLE,
                             reason="No data file was supplied. This command reads one "
                                    "spreadsheet or CSV; it does not choose a file.")

    source_path = os.path.abspath(source)
    before = source_sha256(source_path)
    try:
        result = pipeline_mod.run(source, **pipeline_kwargs)
    except BusinessOpsError as exc:
        return CommandResult(spec, source=source, question=question,
                             presentation=presentation, routing=routing,
                             status=UNAVAILABLE, reason=str(exc),
                             error_type=type(exc).__name__)

    # Which engine this command drives is declared in the registry, not decided here.
    # A forecast and an anomaly scan are separate entry points on the pipeline for the
    # same reason the analytics layer is: they answer a different question and are
    # refused under different conditions.
    analyses = {}
    if spec.engine == registry_mod.FORECAST_ENGINE:
        pipeline_mod.forecast(
            result, targets=engine_args.get("targets"),
            horizon=engine_args.get("horizon"), presentation=presentation,
            method_id=engine_args.get("method"))
        analyses = result.analyses
    elif spec.engine == registry_mod.ANOMALY_ENGINE:
        pipeline_mod.detect_anomalies(
            result, metrics=engine_args.get("metrics"), presentation=presentation,
            sensitivity=engine_args.get("sensitivity"))
        analyses = result.analyses
    else:
        domains = _domains_for(spec, routing)
        if domains:
            analyses = pipeline_mod.analyse(result, domains=list(domains),
                                            presentation=presentation)

    status, reason = OK, None
    if result.halted:
        status, reason = HALTED, result.halt_reason

    # The source is hashed again once every engine has run. Bytes that changed underneath the
    # run make the run unusable rather than silently mixing two versions of the data.
    if before is None or source_sha256(source_path) != before:
        return CommandResult(spec, source=source, question=question,
                             presentation=presentation, routing=routing,
                             status=UNAVAILABLE, reason=SOURCE_CHANGED,
                             error_type="SourceChanged")

    command_result = CommandResult(spec, source=source, question=question,
                                   presentation=presentation, result=result,
                                   analyses=analyses, routing=routing,
                                   status=status, reason=reason)
    _record_basis(command_result, source_path, before, run_arguments)

    if routing is not None:
        from ..kpi import primitives as kpi_primitives
        answer = query_mod.resolve(
            routing, result.kpis, analyses, semantic_map=result.semantic_map,
            periods=kpi_primitives.periods(result.dataset, result.semantic_map))
        command_result.answer = answer
        if status == OK and not answer.answered:
            command_result.status = UNAVAILABLE
            command_result.reason = answer.reason

    # A command that cannot see the roles it needs says so rather than reporting an
    # empty analysis as though nothing had happened.
    if command_result.status == OK:
        missing = [role for role in spec.required_roles
                   if not result.semantic_map.column_for(role)]
        if missing:
            command_result.status = UNAVAILABLE
            command_result.reason = (
                "%s needs a column mapped to %s; none was identified in this dataset."
                % (spec.title, " and ".join(missing)))

    return command_result


def run_all(source, presentation=presentation_mod.LOCAL, question=None,
            **pipeline_kwargs):
    """Every command over one source — used by the demo validation and the tests."""
    out = {}
    for command_id in registry_mod.COMMAND_IDS:
        out[command_id] = run(command_id, source, question=question,
                              presentation=presentation, **pipeline_kwargs)
    return out
