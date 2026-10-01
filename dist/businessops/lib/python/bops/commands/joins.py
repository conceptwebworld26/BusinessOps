# -*- coding: utf-8 -*-
"""The local join: an internal result and a public benchmark in one strict set.

ADR-0009 makes the local join the **default** answer to a comparative question — "is our
margin typical?" is a question about the industry, not about us, so the query carries only
public terms, the benchmark comes back, and the comparison is computed here. M10.1 built
both halves of the representation that comparison needs. M10.2-R.10 through R.13 made the
**external** half user-reachable: four research commands now reach
`synthesis.footed_statement()` through their real paths. The internal half never moved.
`from_analysis_set()` and `from_kpi_result()` were implemented, tested and called by nothing
outside the test suite, so the one capability the seven-dimension footing architecture exists
to authorise — setting our number beside theirs — had no user-reachable surface at all.

This module is that surface's engine half:

    commands.run(...)              -> CommandResult holding genuine AnalysisSet / KPIResult
    research.close_retrieval_object(...) -> genuine EvidenceSet            (ADR-0024)
    local_join(...)                -> from_analysis_set / from_kpi_result   (internal side)
                                   -> synthesis.footed_statement()          (external side)
                                   -> one SynthesisSet(require_dimension_provenance=True)
                                   -> synthesis.compare_values()

**The module is `joins.py`, not `local_join.py`.** `from .joins import local_join` binds the
function in the package namespace; had the module shared that name, the function would have
shadowed the module and `bops.commands.local_join` would resolve to a callable rather than to
the module it came from. `research/intents.py` holding `intent()` is the same convention.

**It lives in the orchestration layer, and that is not an accident.** A local join needs a
`CommandResult`, which the command layer owns; `synthesis/` sits *below* the command layer
and may not depend upward (CLAUDE.md §2.3). Putting the seam here keeps the dependency
pointing down — orchestration reads synthesis, analytics and research, never the reverse —
and leaves the synthesis package with no knowledge that commands exist.

**It decides nothing.** It computes no figure, authors no footing, resolves no dimension,
compares no values itself and holds no privacy rule. Every one of those already has a home:
the analytics engine and the KPI engine compute, `from_analysis_set`/`from_kpi_result`
translate, `source_footings`/`resolve()` admit, `compatibility.compare()` decides
comparability, and the disclosure gate governs what may leave. What this module adds is
ordering, and the refusals that stop the ordering being skipped.

**The privacy property is structural, not procedural.** This module imports no gate, no
query builder and no retrieval request; it cannot construct or alter an outbound query even
if asked. It receives a retrieval that has **already closed**, which means the external
request was built, authorised, dispatched and normalised before any internal figure was in
scope. The join therefore happens strictly after retrieval, and the internal value has
nowhere to go: there is no code path from here to anything outbound. A test asserts the
absent imports, which is a stronger guarantee than a rule someone has to follow.
"""

from collections import namedtuple

from ..analytics import contract as analytics_contract
from ..kpi import contract as kpi_contract
from .. import synthesis as synthesis_mod
from ..synthesis import contract as synthesis_contract
from . import runner as runner_mod

#: The one status a completed command run carries. A halted or unavailable run has no
#: analysis to join, and inventing one is the failure this refuses.
OK = runner_mod.OK

#: Fields this path sets on the internal side. A caller supplying one would be describing
#: the same analysis twice, and two descriptions of one figure can disagree.
RESERVED_INTERNAL_FIELDS = ("analysis_set", "result", "synthesis")


class LocalJoin(namedtuple("LocalJoin",
                           "synthesis internal external comparison")):
    """One internal statement, one external statement, and what the comparison found.

    `internal` and `external` are the two `SynthesisItem`s that were compared; `comparison`
    is `compatibility.compare()`'s record, or `None` where the caller asked for the join
    without the comparison. All three are **views** of what the set already decided —
    nothing here can change a verdict, and no combined figure exists anywhere in it.
    """

    __slots__ = ()

    @property
    def compatible(self):
        """Whether the two figures measure the same quantity. Never a recommendation."""
        if self.comparison is None:
            return None
        return synthesis_mod.may_combine(self.comparison)

    def as_dict(self):
        """The record a markdown command reads off stdout. No figure is combined here."""
        record = {
            "internal_id": self.internal.id if self.internal is not None else None,
            "external_id": self.external.id if self.external is not None else None,
            "internal_origin": self.internal.origin if self.internal is not None else None,
            "external_origin": self.external.origin if self.external is not None else None,
        }
        if self.comparison is not None:
            record.update({
                "status": self.comparison["status"],
                "matched": list(self.comparison["matched"]),
                "mismatched": [m["dimension"] for m in self.comparison["mismatched"]],
                "unknown": [u["dimension"] for u in self.comparison["unknown"]],
                "may_combine": synthesis_mod.may_combine(self.comparison),
                "converted": self.comparison["converted"],
            })
        return record


def internal_result(command_result):
    """The genuine `CommandResult` a completed command run produced, or a refusal.

    `type(...) is CommandResult` for the reason every other identity check in this codebase
    is strict: a subclass may never have run `__init__`, and a look-alike carries none of
    the pipeline, quality gate, analytics or KPI objects the translators need. A serialised
    result is refused for the same reason `register_external()` refuses a serialised
    evidence set — it would carry its own provenance as data.
    """
    if type(command_result) is not runner_mod.CommandResult:
        raise synthesis_contract.SynthesisError(
            "the internal side of a local join is the CommandResult a real command run "
            "produced; a dict, a subclass or a look-alike carries none of the analysis, "
            "KPI or quality objects the internal translators require")
    if command_result.status != OK:
        raise synthesis_contract.SynthesisError(
            "the command run did not complete (status %r), so there is no internal "
            "analysis to join. A halted or unavailable run produces no statement rather "
            "than an unfooted one." % (command_result.status,))
    if command_result.halted:
        raise synthesis_contract.SynthesisError(
            "the data quality gate halted this run; its findings are not analysis and do "
            "not enter synthesis")
    return command_result


def _strict_set(synthesis, subject):
    if synthesis is None:
        return synthesis_mod.SynthesisSet(subject=subject,
                                          require_dimension_provenance=True)
    if not isinstance(synthesis, synthesis_mod.SynthesisSet):
        raise synthesis_contract.SynthesisError(
            "a local join may be added only to a SynthesisSet")
    if not synthesis.require_dimension_provenance:
        raise synthesis_contract.SynthesisError(
            "a local join belongs only in a set built with "
            "require_dimension_provenance=True. Without it an external dimension the "
            "caller declared but no source footed passes through unchecked, which is the "
            "pass-through ADR-0026 closes and the whole reason the external half of this "
            "join exists.")
    return synthesis


def internal_statements(synthesis, command_result, origin, dataset_id,
                        kpi_id=None, domains=None, statement=None, **dimensions):
    """Translate one completed command run into internal statements. Reuses the translators.

    With `kpi_id`, the named `KPIResult` goes through `from_kpi_result()`; without it, every
    analysis the command declared goes through `from_analysis_set()`. Both are the M10.1
    translators unchanged — this function chooses between them and supplies the dataset
    registration they need, and does nothing else. It computes no figure and re-judges no
    materiality.

    `dimensions` are the comparability dimensions the analytics engine does not itself carry
    — `metric_definition`, `geography`, `scope`, `methodology`, and `period` where the
    finding has none. They describe **our own** analysis, they are passed straight to the
    translator, and they never travel anywhere: an internal statement is engine-footed on
    the registered dataset (ADR-0023) and carries no dimension provenance at all.
    """
    if not dataset_id or not str(dataset_id).strip():
        raise synthesis_contract.SynthesisError(
            "an internal statement must name the dataset it rests on; ADR-0023 refuses an "
            "internal calculation that is not internally footed")
    synthesis.register_dataset(str(dataset_id),
                               label=command_result.source,
                               detail=command_result.command_id)
    run_id = getattr(command_result, "run_id", None)

    if kpi_id is not None:
        result = command_result.kpis.get(kpi_id)
        if result is None:
            raise synthesis_contract.SynthesisError(
                "this command run produced no KPI %r; a local join cites a metric the "
                "engine actually computed, never one named in hope" % (kpi_id,))
        # Every refusal happens before anything run-related is registered (ADR-0035).
        if run_id:
            synthesis.check_run_binding(synthesis_contract.P_KPI, kpi_id, run_id)
            _register_run(synthesis, command_result, dataset_id)
        produced = synthesis_mod.from_kpi_result(
            synthesis, result, dataset_id=str(dataset_id), statement=statement,
            **dimensions)
        # `from_kpi_result` records a limitation and returns None for an unavailable KPI.
        # That is its behaviour and it is correct; the join reports it rather than inventing
        # a figure, so the caller sees an unavailable metric instead of a fabricated one.
        if produced is None:
            raise synthesis_contract.SynthesisError(
                "KPI %r is unavailable on this dataset, and an unavailable metric is a "
                "limitation rather than a statement. The set records why; nothing is "
                "estimated to fill it." % (kpi_id,))
        if run_id:
            synthesis.bind_run(synthesis_contract.P_KPI, kpi_id, run_id)
        return [produced]

    keys = tuple(domains) if domains is not None else command_result.analysis_keys
    analyses = []
    for name in keys:
        analysis = command_result.analyses.get(name)
        if analysis is None:
            continue
        if not isinstance(analysis, analytics_contract.AnalysisSet):
            raise synthesis_contract.SynthesisError(
                "%r is not an AnalysisSet; only the analytics engine's own object may be "
                "translated into internal statements" % (name,))
        analyses.append(analysis)
    # Every refusal happens before anything run-related is registered (ADR-0035).
    if run_id:
        for analysis in analyses:
            kind = synthesis.analysis_kind(analysis)
            for finding in analysis.findings:
                synthesis.check_run_binding(kind, finding.analysis_id, run_id)
        if analyses:
            _register_run(synthesis, command_result, dataset_id)
    produced = []
    for analysis in analyses:
        produced.extend(synthesis_mod.from_analysis_set(
            synthesis, analysis, origin, dataset_id=str(dataset_id), **dimensions))
        if run_id:
            kind = synthesis.analysis_kind(analysis)
            for finding in analysis.findings:
                synthesis.bind_run(kind, finding.analysis_id, run_id)
    if not produced:
        raise synthesis_contract.SynthesisError(
            "the command run produced no analytical finding to join")
    return produced


def _register_run(synthesis, command_result, dataset_id):
    """Register the run's recomputation basis where the run carries one (ADR-0035)."""
    if getattr(command_result, "run_id", None) is None:
        return None
    return synthesis.register_run(command_result, dataset_id)


def kpi_statements(synthesis, command_result, dataset_id):
    """Register every KPI of one command run, bound to that run. Reuses the KPI translator.

    Each `KPIResult` goes through `from_kpi_result()` in KPI catalogue order: a value-bearing
    KPI becomes a statement; an unavailable one is recorded as a limitation and never
    estimated. Every registration is bound to the run, so a report's scorecard can be
    recomputed (ADR-0035 section 2). Computes no figure and re-judges nothing.
    """
    if not dataset_id or not str(dataset_id).strip():
        raise synthesis_contract.SynthesisError(
            "an internal statement must name the dataset it rests on; ADR-0023 refuses an "
            "internal calculation that is not internally footed")
    from ..kpi import catalog as kpi_catalog
    kpis = command_result.kpis
    order = [d.kpi_id for d in kpi_catalog.CATALOGUE if d.kpi_id in kpis]
    order += sorted(k for k in kpis if k not in order)
    run_id = getattr(command_result, "run_id", None)
    # Every refusal happens before anything is registered (ADR-0035).
    if run_id:
        for kpi_id in order:
            synthesis.check_run_binding(synthesis_contract.P_KPI, kpi_id, run_id)
    synthesis.register_dataset(str(dataset_id), label=command_result.source,
                               detail=command_result.command_id)
    if run_id:
        _register_run(synthesis, command_result, dataset_id)
    produced = []
    for kpi_id in order:
        item = synthesis_mod.from_kpi_result(synthesis, kpis[kpi_id],
                                             dataset_id=str(dataset_id))
        if run_id:
            synthesis.bind_run(synthesis_contract.P_KPI, kpi_id, run_id)
        if item is not None:
            produced.append(item)
    return produced


def _select(statements, metric):
    """The one internal statement the comparison is about. Deterministic, never guessed."""
    if metric is None:
        if len(statements) != 1:
            raise synthesis_contract.SynthesisError(
                "this run produced %d internal statements; name the metric to compare "
                "rather than letting the join pick one" % len(statements))
        return statements[0]
    matches = [item for item in statements if item.metric == metric]
    if not matches:
        raise synthesis_contract.SynthesisError(
            "no internal statement carries metric %r; the engine computed %s"
            % (metric, ", ".join(sorted(set(str(i.metric) for i in statements)))))
    if len(matches) > 1:
        raise synthesis_contract.SynthesisError(
            "metric %r appears on %d internal statements in this run; a comparison must "
            "name one figure, so narrow the run or the period rather than comparing an "
            "ambiguous pair" % (metric, len(matches)))
    return matches[0]


def local_join(command_result, retrieval, origin, statement, figure_evidence_id,
               dataset_id, internal_metric=None, internal_kpi=None,
               internal_origin=None, internal_dimensions=None, internal_statement=None,
               domains=None, stated=None, context=None, context_evidence_id=None,
               applicability=None, locator=None, context_locator=None,
               synthesis=None, subject=None, compare=True, **statement_fields):
    """Put one internal figure and one footed external figure in one strict set.

    The internal side comes from a completed command run through the M10.1 translators; the
    external side comes from a completed retrieval through the R.10 footing seam. Both
    arrive already made: this function orders them, and orders nothing else.

    Returns a `LocalJoin`. Raises `SynthesisError` where the path itself was not followed;
    a comparison that merely fails is not an error — it is an `incompatible` or `unknown`
    verdict, returned in `comparison` with the dimension that failed, and recorded as a
    limitation by `compare_values()` exactly as it always has been.
    """
    command_result = internal_result(command_result)
    owned = sorted(set(statement_fields) & set(RESERVED_INTERNAL_FIELDS))
    if owned:
        raise synthesis_contract.SynthesisError(
            "%s belongs to the command run and may not be supplied here"
            % ", ".join(owned))

    synthesis = _strict_set(synthesis, subject or command_result.command_id)

    internal = _select(
        internal_statements(
            synthesis, command_result,
            internal_origin or synthesis_mod.ORIGIN_FINANCIAL, dataset_id,
            kpi_id=internal_kpi, domains=domains, statement=internal_statement,
            **dict(internal_dimensions or {})),
        internal_metric)

    external = synthesis_mod.footed_statement(
        retrieval, origin, statement, figure_evidence_id, stated=stated,
        context=context, context_evidence_id=context_evidence_id,
        applicability=applicability, locator=locator, context_locator=context_locator,
        synthesis=synthesis, **statement_fields)

    comparison = None
    if compare:
        comparison = synthesis_mod.compare_values(synthesis, internal, external.statement)
    return LocalJoin(synthesis, internal, external.statement, comparison)
