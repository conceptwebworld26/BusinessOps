"""The canonical synthesis result: one auditable set of statements over many domains.

This is the object SWOT, strategy, decision support and executive reporting will read. It
holds statements, the source objects those statements point at, the disagreements between
them, what could not be done, and how confident any of it is - and it derives the last
three rather than accepting them, because a conclusion supplied by a caller is a
conclusion nobody checked.

The shape of the defence is worth stating once. Every guarantee in this module is
structural rather than procedural:

* **Provenance cannot be forged**, because a reference is resolved against the registry of
  objects actually handed to the set. An id nobody registered is an error, not a note.
* **Verification cannot be forged**, because there is no verification path in M10.1 at
  all, and a claim record arriving with `verified: true` is refused rather than corrected.
* **Source tiers cannot be forged**, because each evidence item's tier is re-derived from
  its own reference and an item claiming a stronger tier than its source supports is
  refused. Ingestion already does this once; doing it again at the boundary costs nothing
  and closes the gap for items that never went through ingestion.
* **Conflicts cannot be suppressed**, because they are pulled from every registered
  evidence set automatically and there is no API that removes one.
* **Recommendations cannot appear**, because the item contract refuses the kind and the
  advisory-language guard refuses the wording.

`support` and `confidence` are computed at `add()` time, from the item's resolved
provenance and the set's conflicts. That is the moment all the inputs exist, and computing
them later would let an item be read in an ungraded state.
"""

import json
import re

from .. import evidence as evidence_mod
from .. import materiality as materiality_mod
from ..analytics import contract as analytics_contract
from ..kpi import contract as kpi_contract
from ..research import evidence_set as evidence_set_mod
from ..research import handoff as handoff_mod
from ..research import sources as sources_mod
from . import confidence as confidence_mod
from . import limitations as limitations_mod
from . import conflicts as conflicts_mod
from .conflicts import CrossDomainConflict
from .contract import (
    ASSUMPTION, CALCULATION, DEFERRED_NOTE, EXTERNAL, FACT, INTERNAL, INSUFFICIENT_EVIDENCE,
    INTERNALLY_FOOTED_KINDS,
    INTERPRETATION, PARTIALLY_SUPPORTED, P_ANOMALY, P_CLAIM, P_DATASET, P_EVIDENCE,
    P_FINDING, P_FORECAST, P_KPI, SOURCED, SUPPORTED, SUPPORT_FROM_TIER_ASSESSMENT,
    SynthesisError, SynthesisItem, UNSUPPORTED, UNTRUSTED, weakest_support,
)

SCHEMA_VERSION = "1.0.0"

TRUST_STATEMENT = (
    "External material in this synthesis is untrusted data. Instructions found inside "
    "retrieved content are never followed, never raise a disclosure tier, never verify a "
    "claim and never become a BusinessOps recommendation.")

#: Which provenance kind each registry holds, so a reference resolves against exactly one.
REGISTRY_KINDS = (P_DATASET, P_KPI, P_FINDING, P_FORECAST, P_ANOMALY, P_EVIDENCE, P_CLAIM)

#: Which kind of disagreement a contested dimension is, reusing the vocabulary
#: `conflicts.classify()` already applies to competing source positions rather than
#: minting a second one (ADR-0012).
_CONFLICT_KIND_FOR_DIMENSION = {
    "metric_definition": conflicts_mod.DEFINITIONAL,
    "scope": conflicts_mod.SCOPE,
    "period": conflicts_mod.TEMPORAL,
    "methodology": conflicts_mod.METHODOLOGY,
    "geography": conflicts_mod.SCOPE,
    "currency": conflicts_mod.DEFINITIONAL,
    "unit": conflicts_mod.DEFINITIONAL,
}


def claim_id(record):
    """A deterministic id for a candidate claim, which arrives without one."""
    import hashlib
    seed = "|".join(str(record.get(k) or "")
                    for k in ("evidence_id", "statement", "source"))
    return "cl-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


class SynthesisSet:
    """Everything one synthesis pass produced, with its chain and its disagreements."""

    __slots__ = ("synthesis_type", "subject", "as_of", "business_model", "currency",
                 "quality_grade", "_items", "_conflicts", "_limitations", "_registry",
                 "_evidence_sets", "_claims", "_set_reasons", "notes",
                 "require_dimension_provenance", "_runs", "_run_of")

    def __init__(self, synthesis_type="cross_domain", subject=None, as_of=None,
                 business_model=None, currency=None, quality_grade=None, notes=None,
                 require_dimension_provenance=False):
        self.synthesis_type = synthesis_type
        self.subject = subject
        self.as_of = as_of
        self.business_model = business_model
        self.currency = currency
        self.quality_grade = quality_grade
        self._items = []
        self._conflicts = []
        self._limitations = []
        self._registry = dict((kind, {}) for kind in REGISTRY_KINDS)
        self._evidence_sets = []
        self._claims = []
        self._set_reasons = []
        self.notes = list(notes or [])
        #: ADR-0026. When true, an external statement may not carry a dimension the
        #: evidence did not establish: a declared dimension with no admissible footing
        #: reads as unstated. Default false so the mechanism is strictly additive and
        #: unmigrated callers behave exactly as they did, exactly as ADR-0025 phased in.
        self.require_dimension_provenance = bool(require_dimension_provenance)
        #: ADR-0035 section 2. Each command run a registered KPI or analysis came from, keyed
        #: by its content-addressed `run_id`, and which run each registration belongs to.
        self._runs = {}
        self._run_of = {}

    # -- registration -------------------------------------------------------

    def register_dataset(self, dataset_id, label=None, detail=None):
        """Register the internal dataset a fact may point at."""
        if not dataset_id:
            raise SynthesisError("a dataset provenance source must have an id")
        self._registry[P_DATASET][str(dataset_id)] = {
            "id": str(dataset_id), "label": label, "detail": detail}
        return str(dataset_id)

    def register_run(self, command_result, dataset_id):
        """Register the recomputation basis of one command run (ADR-0035 section 2).

        Idempotent for the same run. The `run_id` is content-addressed over the command, the
        absolute source path, the source's SHA-256, the run arguments and the configuration
        digest, so two runs differ in id exactly when one of those differs.
        """
        run_id = getattr(command_result, "run_id", None)
        if not run_id:
            raise SynthesisError(
                "this command run carries no recomputation basis - its source changed during "
                "the run or the pipeline did not complete - so nothing from it is registered "
                "as recomputable")
        record = {"run_id": run_id, "dataset_id": str(dataset_id),
                  "command_id": command_result.command_id,
                  "source_path": command_result.source_path,
                  "source_sha256": command_result.source_sha256,
                  "run_arguments": command_result.run_arguments,
                  "config_digest": command_result.config_digest}
        held = self._runs.get(run_id)
        if held is not None and held != record:
            raise SynthesisError(
                "run %s is already registered with a different basis; one run carries one "
                "dataset label" % run_id)
        self._runs[run_id] = record
        return run_id

    @staticmethod
    def _run_key(kind, ref_id):
        return "%s:%s" % (kind, ref_id)

    def check_run_binding(self, kind, ref_id, run_id):
        """Refuse a registration another run already owns. Changes nothing (ADR-0035)."""
        held = self._run_of.get(self._run_key(kind, ref_id))
        if held is not None and held != run_id:
            raise SynthesisError(
                "%s %s is already registered from run %s; registering it again from run %s "
                "would silently replace the figures a statement rests on, so it is refused"
                % (kind, ref_id, held, run_id))

    def bind_run(self, kind, ref_id, run_id):
        """Record that a registered KPI or finding came from `run_id`. Idempotent per run."""
        if run_id not in self._runs:
            raise SynthesisError("run %s is not registered in this set" % run_id)
        self.check_run_binding(kind, ref_id, run_id)
        self._run_of[self._run_key(kind, ref_id)] = run_id

    def analysis_kind(self, analysis_set):
        """The provenance kind an analysis set's findings are registered under."""
        return _provenance_kind_for(analysis_set)

    def run_for(self, kind, ref_id):
        """A copy of the run registration a KPI or finding came from, or `None`."""
        run_id = self._run_of.get(self._run_key(kind, ref_id))
        return dict(self._runs[run_id]) if run_id else None

    def registered_runs(self):
        """Every registered run, as copies, in registration order."""
        return [dict(record) for record in self._runs.values()]

    def register_analysis(self, analysis_set):
        """Register an `AnalysisSet` (or any subclass: forecast, anomaly) and its findings.

        Findings are indexed by `analysis_id` under the provenance kind their domain
        implies, so a forecast finding is referenced as a forecast and an anomaly finding
        as an anomaly - the distinction downstream reporting needs.
        """
        if not isinstance(analysis_set, analytics_contract.AnalysisSet):
            raise SynthesisError(
                "only an AnalysisSet (or subclass) may be registered as internal "
                "analysis; a dict cannot carry its own status or limitations")
        kind = _provenance_kind_for(analysis_set)
        for finding in analysis_set.findings:
            self._registry[kind][str(finding.analysis_id)] = finding
        self._limitations = limitations_mod.merge(self._limitations,
                                                  analysis_set.limitations)
        if analysis_set.status == analytics_contract.INSUFFICIENT_DATA:
            self._set_reasons.append(confidence_mod.INSUFFICIENT_HISTORY)
        return analysis_set

    def register_kpi(self, result):
        """Register one `KPIResult`. An unavailable KPI is registered and noted, not hidden."""
        if not isinstance(result, kpi_contract.KPIResult):
            raise SynthesisError("only a KPIResult may be registered as a KPI source")
        self._registry[P_KPI][str(result.kpi_id)] = result
        if result.status == kpi_contract.UNAVAILABLE:
            self._set_reasons.append(confidence_mod.UNAVAILABLE_KPI)
        return result

    def register_evidence_set(self, evidence_set):
        """Register an external `EvidenceSet`, its items, and its conflicts.

        Only the object is accepted. A dict would arrive carrying `source_tier` as data,
        and the whole point of local tiering is that a tier is something BusinessOps
        derives from a source's identity rather than something it is told.
        """
        if not isinstance(evidence_set, evidence_set_mod.EvidenceSet):
            raise SynthesisError(
                "only an EvidenceSet object may be registered as external evidence. A "
                "serialised set would carry its tiers as data; tiers are derived locally "
                "from the source, never accepted from a payload.")
        for item in evidence_set.items:
            _refuse_forged_tier(item)
            self._registry[P_EVIDENCE][str(item.id)] = item
        self._evidence_sets.append(evidence_set)
        for record in evidence_set.conflicts:
            self.add_conflict(CrossDomainConflict.from_evidence_conflict(record))
        return evidence_set

    def register_claims(self, claims):
        """Register candidate claims exactly as `close_retrieval` produced them.

        A record asserting its own verification is refused outright. There is no
        verification path in M10.1, so `verified: true` cannot have been produced by one -
        it was either forged or fabricated, and neither is something to normalise away.
        """
        registered = []
        for record in claims or []:
            if not isinstance(record, dict):
                raise SynthesisError("a candidate claim must be a record")
            if _is_data_profile(record):
                raise SynthesisError(
                    "a data profile, or a part of one, was offered as a candidate claim. A "
                    "profile describes the structure of files; it is diagnostic metadata, not "
                    "evidence about the business, and it never enters synthesis (ADR-0036).")
            if _is_connector_material(record):
                raise SynthesisError(
                    "connector material was offered as a candidate claim: a connector "
                    "catalogue, a part of one, a resolution, a brief, or a claim of class 2 "
                    "(connected-system data). A catalogue is connector-reported structure "
                    "relayed by a model and is never evidence, and no path in this version "
                    "produces a legitimate class-2 claim, so none enters synthesis "
                    "(ADR-0037 section I).")
            if _is_recommendation(record):
                raise SynthesisError(
                    "a recommendation was offered as a candidate claim. A recommendation is "
                    "class 7 - advice built from this layer's statements - and it never "
                    "re-enters the evidence it was built from, whatever form it arrives in "
                    "(ADR-0031); nor does a decision package or any of its parts (ADR-0032), "
                    "nor an executive report or any of its sections (ADR-0033), nor a "
                    "verification result, a finding or a final artifact (ADR-0034).")
            if record.get("verified") is True:
                raise SynthesisError(
                    "a claim arrived marked verified. No verification path exists in the "
                    "synthesis foundation, so no legitimate producer could have set it; "
                    "the claim is refused rather than downgraded.")
            status = record.get("status")
            if status not in (None, handoff_mod.CANDIDATE):
                raise SynthesisError(
                    "a claim arrived with status %r; only %r is produced by retrieval and "
                    "nothing in synthesis promotes it."
                    % (status, handoff_mod.CANDIDATE))
            stored = dict(record)
            stored["status"] = handoff_mod.CANDIDATE
            stored["verified"] = False
            stored["claim_id"] = stored.get("claim_id") or claim_id(stored)
            self._registry[P_CLAIM][stored["claim_id"]] = stored
            self._claims.append(stored)
            registered.append(stored)
        return registered

    # -- assembly -----------------------------------------------------------

    def add(self, item):
        """Add one statement, resolving its provenance and grading it.

        Grading happens here rather than on read because every input exists at this
        moment: the registries are populated, the conflicts are known, and the item's own
        materiality has been decided by the materiality policy upstream.
        """
        if not isinstance(item, SynthesisItem):
            raise SynthesisError("only a SynthesisItem may enter a synthesis set")

        unresolved = self._unresolved_refs(item)
        if unresolved:
            raise SynthesisError(
                "provenance references no registered source object: %s. A statement "
                "cannot cite material this set was never given."
                % ", ".join("%s:%s" % ref for ref in unresolved))

        self._require_internal_footing(item)
        self._resolve_dimensions(item)

        item.conflict_refs = sorted(self._conflicts_touching(item))
        item.support, item.support_detail = self._assess_support(item)

        if item.is_material and item.support in (SUPPORTED, PARTIALLY_SUPPORTED) \
                and not item.has_provenance():
            raise SynthesisError(
                "a material statement cannot be supported without a traceable chain; "
                "mark it unsupported or insufficient_evidence instead")

        assessment = confidence_mod.assess(self._confidence_reasons(item))
        item.confidence = assessment.level
        item.confidence_detail = assessment.as_dict()

        self._limitations = limitations_mod.merge(self._limitations, item.limitations)
        self._items.append(item)
        return item

    def add_conflict(self, conflict):
        """Record a disagreement. There is deliberately no matching removal."""
        if not isinstance(conflict, CrossDomainConflict):
            raise SynthesisError("only a CrossDomainConflict may be recorded")
        if any(existing.id == conflict.id for existing in self._conflicts):
            return conflict
        self._conflicts.append(conflict)
        if conflict.unresolved:
            self.limit(limitations_mod.UNRESOLVED_CONFLICT, conflict.subject,
                       conflict.reason)
        # A conflict recorded after the items it touches must still reach them, or the
        # order of two calls would decide whether a statement looks contested.
        for item in self._items:
            self._regrade(item)
        return conflict

    def limit(self, code, subject, reason, status=analytics_contract.UNAVAILABLE):
        limitation = limitations_mod.Limitation(code, subject, reason, status)
        self._limitations = limitations_mod.merge(self._limitations, [limitation])
        return limitation

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    # -- provenance ---------------------------------------------------------

    def _require_internal_footing(self, item):
        """Refuse an internal FACT or CALCULATION that rests on no internal source.

        The kind/domain constraint in `contract` decides what a statement may *call*
        itself given the origin the caller declared. This decides whether the declaration
        is borne out by the chain actually attached, and it is a separate question: a
        caller naming `ORIGIN_FINANCIAL` while citing one tier-C evidence item satisfies
        the first check and fails this one.

        Resolution is against the registries, never against the item. `domain`, `origin`,
        `trust`, `evidence_class` and any tier on the cited object are all caller- or
        payload-influenced, so none of them is read here; the question asked is only
        whether a reference points at an internal object this set was actually given.
        """
        if item.kind not in INTERNALLY_FOOTED_KINDS or item.domain != INTERNAL:
            return

        grounded = [ref for ref in item.internal_refs()
                    if self.resolve_ref(ref) is not None]
        if grounded:
            return

        cited = ", ".join(sorted(set(ref.kind for ref in item.provenance))) or "nothing"
        raise SynthesisError(
            "an internal %s must rest on at least one internal source this set holds - a "
            "dataset, calculation, KPI, finding, forecast or anomaly - and this one cites "
            "%s. External evidence does not become an internal statement by being cited "
            "from one: what a source said is %s, and a reading of it is %s."
            % (item.kind, cited, SOURCED, INTERPRETATION))

    def _resolve_dimensions(self, item):
        """Decide which of the seven dimensions the evidence actually established.

        Placed here for the same reason `_require_internal_footing` is: resolution needs
        the registries, and the registries exist on the set. The verdict is stored on the
        item as a derived field, so `compare()` reads an already-resolved view and needs no
        knowledge of provenance, evidence or tiers (ADR-0026).
        """
        from . import dimension_provenance as dp_mod

        values, records = dp_mod.resolve(self, item)
        item._resolved_dimensions = values
        item.dimension_resolution = records

        for dimension in dp_mod.conflicting_dimensions(records):
            positions = [dict(r, domain=item.domain) for r in records
                         if r.get("dimension") == dimension and r.get("admitted")]
            if len(positions) < 2:
                continue
            self.add_conflict(CrossDomainConflict(
                conflicts_mod.METHODOLOGY if dimension == "methodology"
                else _CONFLICT_KIND_FOR_DIMENSION.get(dimension,
                                                      conflicts_mod.DEFINITIONAL),
                "%s: %s" % (item.metric or item.id, dimension),
                positions,
                reason=("Two admissible sources establish different values for %s. "
                        "Neither is preferred: the dimension is left unresolved and both "
                        "positions are kept." % dimension),
                domains=(item.domain,),
                item_ids=[item.id]))

    def _unresolved_refs(self, item):
        missing = []
        for ref in item.provenance:
            if not ref.is_resolvable:
                continue
            if str(ref.ref_id) not in self._registry.get(ref.kind, {}):
                missing.append((ref.kind, ref.ref_id))
        return missing

    def resolve_ref(self, ref):
        """The registered object a reference points at, or `None` for unavailable.

        Named `resolve_ref` rather than `resolve` so that nothing on a set that holds
        conflicts reads as an offer to settle one. There is no such method.
        """
        if not ref.is_resolvable:
            return None
        return self._registry.get(ref.kind, {}).get(str(ref.ref_id))

    def chain(self, item):
        """The full supporting chain for one statement, for "where did this come from"."""
        entries = []
        for ref in item.provenance:
            resolved = self.resolve_ref(ref)
            entry = {"kind": ref.kind, "ref_id": ref.ref_id, "label": ref.label,
                     "detail": ref.detail, "resolved": resolved is not None}
            if ref.kind == P_EVIDENCE and resolved is not None:
                entry.update({"source": resolved.source, "reference": resolved.reference,
                              "source_tier": resolved.source_tier,
                              "publication_date": resolved.publication_date,
                              "retrieved_at": resolved.retrieved_at,
                              "freshness": resolved.freshness["freshness"],
                              "trust": resolved.trust})
            elif ref.kind == P_CLAIM and resolved is not None:
                entry.update({"statement": resolved.get("statement"),
                              "evidence_id": resolved.get("evidence_id"),
                              "status": resolved.get("status"),
                              "verified": resolved.get("verified")})
            elif resolved is not None and hasattr(resolved, "as_dict"):
                record = resolved.as_dict()
                entry.update({"statement": record.get("statement"),
                              "basis": record.get("basis") or record.get("formula"),
                              "analysis_type": record.get("analysis_type")})
            entries.append(entry)
        return entries

    # -- support ------------------------------------------------------------

    def _assess_support(self, item):
        """Grade a statement from what it actually cites.

        Internal and external legs are graded separately and the **weaker** wins, because
        a statement citing both is a cross-domain statement and is only as good as its
        weakest leg. A statement citing only internal computation is supported by that
        computation; tiering is a property of external sources and does not apply to it.
        """
        detail = {"internal": None, "external": None, "conflict_downgrade": False}
        verdicts = []

        internal_refs = item.internal_refs()
        if internal_refs:
            detail["internal"] = {
                "support": SUPPORTED,
                "refs": ["%s:%s" % (r.kind, r.ref_id) for r in internal_refs],
                "reason": ("Computed by the engine from the registered dataset or "
                           "analysis; internal provenance is resolvable and complete."),
            }
            verdicts.append(SUPPORTED)

        external_refs = item.external_refs()
        if external_refs:
            tiers = []
            for ref in external_refs:
                resolved = self.resolve_ref(ref)
                if resolved is None:
                    continue
                if ref.kind == P_EVIDENCE:
                    tiers.append(resolved.source_tier)
                else:
                    evidence = self._registry[P_EVIDENCE].get(
                        str(resolved.get("evidence_id")))
                    if evidence is not None:
                        tiers.append(evidence.source_tier)
            assessment = sources_mod.assess_support(tiers, material=item.is_material)
            verdict = SUPPORT_FROM_TIER_ASSESSMENT[assessment["support"]]
            detail["external"] = dict(assessment, support=verdict)
            verdicts.append(verdict)

        if not verdicts:
            detail["reason"] = ("No resolvable supporting material was linked; support "
                                "could not be assessed.")
            return INSUFFICIENT_EVIDENCE, detail

        support = weakest_support(verdicts)

        if item.conflict_refs and support == SUPPORTED:
            support = PARTIALLY_SUPPORTED
            detail["conflict_downgrade"] = True
            detail["conflict_refs"] = list(item.conflict_refs)

        detail["reason"] = (
            "Weakest of the internal and external assessments; a statement resting on "
            "two legs is no stronger than its weaker leg.")
        return support, detail

    def _conflicts_touching(self, item):
        """Conflict ids whose positions cite something this statement also cites."""
        cited_evidence = set()
        for ref in item.provenance:
            if ref.kind == P_EVIDENCE:
                cited_evidence.add(str(ref.ref_id))
            elif ref.kind == P_CLAIM:
                claim = self._registry[P_CLAIM].get(str(ref.ref_id))
                if claim and claim.get("evidence_id"):
                    cited_evidence.add(str(claim["evidence_id"]))

        touching = set()
        for conflict in self._conflicts:
            if not conflict.unresolved:
                continue
            if cited_evidence & set(str(e) for e in conflict.evidence_ids):
                touching.add(conflict.id)
            elif item.id in conflict.item_ids:
                touching.add(conflict.id)
        return touching

    def _confidence_reasons(self, item):
        reasons = list(item.confidence_reasons)

        if item.support == UNSUPPORTED:
            reasons.append(confidence_mod.UNSUPPORTED_STATEMENT)
        elif item.support == INSUFFICIENT_EVIDENCE:
            reasons.append(confidence_mod.INSUFFICIENT_EVIDENCE)
        elif item.support == PARTIALLY_SUPPORTED:
            external = (item.support_detail or {}).get("external") or {}
            if external.get("usable_tiers") and set(external["usable_tiers"]) == {"C"}:
                reasons.append(confidence_mod.TIER_C_ONLY)

        if item.conflict_refs:
            reasons.append(confidence_mod.UNRESOLVED_CONFLICT)

        if any(ref.kind == "unavailable" for ref in item.provenance) \
                and not item.has_provenance():
            reasons.append(confidence_mod.PROVENANCE_UNAVAILABLE)

        for ref in item.external_refs():
            resolved = self.resolve_ref(ref)
            evidence = None
            if ref.kind == P_EVIDENCE:
                evidence = resolved
            elif resolved is not None:
                evidence = self._registry[P_EVIDENCE].get(
                    str(resolved.get("evidence_id")))
            if evidence is None:
                continue
            freshness = evidence.freshness["freshness"]
            if freshness == sources_mod.UNDATED:
                reasons.append(confidence_mod.UNDATED_EXTERNAL)
            elif freshness == sources_mod.DATED:
                reasons.append(confidence_mod.STALE_EXTERNAL)

        if self.quality_grade is not None:
            from ..quality import contract as quality_contract
            if self.quality_grade == quality_contract.WARNING:
                reasons.append(confidence_mod.DATA_QUALITY_WARNING)

        return reasons

    def _regrade(self, item):
        item.conflict_refs = sorted(self._conflicts_touching(item))

        item.support, item.support_detail = self._assess_support(item)
        assessment = confidence_mod.assess(self._confidence_reasons(item))
        item.confidence = assessment.level
        item.confidence_detail = assessment.as_dict()

    # -- views --------------------------------------------------------------

    @property
    def items(self):
        return list(self._items)

    @property
    def conflicts(self):
        """A copy. There is no removal API, and handing out the list would create one."""
        return list(self._conflicts)

    @property
    def limitations(self):
        return list(self._limitations)

    @property
    def candidate_claims(self):
        return [dict(record) for record in self._claims]

    @property
    def recommendations(self):
        """Reserved, and always empty in the synthesis foundation."""
        return []

    def registered_kpis(self):
        """Every `KPIResult` this set registered, in registration order. A new list; read-only.

        Includes KPIs that could not be computed: an unavailable metric is registered and
        noted, never hidden, and a reader of the set must be able to say so (ADR-0033).
        """
        return list(self._registry[P_KPI].values())

    def registered_datasets(self):
        """Every internal dataset this set registered, as copies, in registration order."""
        return [dict(record) for record in self._registry[P_DATASET].values()]

    def registered_evidence_sets(self):
        """`{operation, subject, category}` for each external evidence set registered, in order.

        Labels only: the items stay reachable through the statements that cite them, and a
        tier is never read from here.
        """
        return [{"operation": evidence_set.operation, "subject": evidence_set.subject,
                 "category": evidence_set.category} for evidence_set in self._evidence_sets]

    def of_kind(self, kind):
        return [item for item in self._items if item.kind == kind]

    def of_domain(self, domain):
        return [item for item in self._items if item.domain == domain]

    def of_origin(self, origin):
        return [item for item in self._items if item.origin == origin]

    def material(self):
        return [item for item in self._items if item.is_material]

    def unresolved_conflicts(self):
        return [c for c in self._conflicts if c.unresolved]

    def confidence(self):
        """The set-level verdict: the weakest statement, with every reason pooled."""
        assessments = [confidence_mod.assess(
            (item.confidence_detail or {}).get("reasons") or []) for item in self._items]
        return confidence_mod.combine(assessments, extra_reasons=sorted(set(
            self._set_reasons)))

    def support_counts(self):
        counts = {}
        for item in self._items:
            counts[item.support] = counts.get(item.support, 0) + 1
        return dict(sorted(counts.items()))

    def record_in(self, ledger):
        """Append every statement to an evidence ledger, preserving its class.

        The ledger enforces its own rules and is not softened here: a `SOURCED` statement
        must supply all four external fields or `Claim` refuses it, which is exactly the
        guarantee that an uncited external figure cannot reach a report.
        """
        recorded = []
        for item in self._items:
            kwargs = {"confidence": item.confidence, "caveats": list(item.caveats),
                      "based_on": [ref.ref_id for ref in item.provenance if ref.ref_id]}
            if item.kind == CALCULATION:
                kwargs["formula"] = item.basis
            if item.kind == FACT:
                kwargs["source"] = item.provenance[0].label or item.origin
            if item.kind == SOURCED:
                kwargs.update(self._external_claim_fields(item))
            recorded.append(ledger.add(evidence_mod.Claim(
                item.statement, item.evidence_class, **kwargs)))
        return recorded

    def _external_claim_fields(self, item):
        """The four fields a class-3 claim needs, read from the cited evidence."""
        for ref in item.external_refs():
            resolved = self.resolve_ref(ref)
            if resolved is None:
                continue
            evidence = resolved
            if ref.kind == P_CLAIM:
                evidence = self._registry[P_EVIDENCE].get(
                    str(resolved.get("evidence_id")))
            if evidence is None:
                continue
            return {"source": evidence.source, "citation": evidence.reference,
                    "source_date": evidence.publication_date or evidence.retrieved_at,
                    "source_tier": evidence.source_tier}
        return {}

    # -- serialisation ------------------------------------------------------

    def summary(self):
        by_kind = {}
        for item in self._items:
            by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
        by_domain = {}
        for item in self._items:
            by_domain[item.domain] = by_domain.get(item.domain, 0) + 1
        return {
            "synthesis_type": self.synthesis_type,
            "subject": self.subject,
            "items": len(self._items),
            "by_kind": dict(sorted(by_kind.items())),
            "by_domain": dict(sorted(by_domain.items())),
            "support": self.support_counts(),
            "material": len(self.material()),
            "evidence_items": len(self._registry[P_EVIDENCE]),
            "candidate_claims": len(self._claims),
            "conflicts": len(self._conflicts),
            "unresolved_conflicts": len(self.unresolved_conflicts()),
            "limitations": len(self._limitations),
            "recommendations": 0,
        }

    def provenance_index(self):
        """Every statement id mapped to the source ids it rests on."""
        return dict(sorted(
            (item.id, ["%s:%s" % (ref.kind, ref.ref_id) if ref.ref_id else ref.kind
                       for ref in item.provenance])
            for item in self._items))

    def as_dict(self):
        assessment = self.confidence()
        return {
            "schema_version": SCHEMA_VERSION,
            "synthesis_type": self.synthesis_type,
            "subject": self.subject,
            "as_of": self.as_of,
            "business_model": self.business_model,
            "currency": self.currency,
            "quality_grade": self.quality_grade,
            "trust": UNTRUSTED,
            "trust_statement": TRUST_STATEMENT,
            "items": [item.as_dict() for item in self._items],
            "facts": [i.id for i in self.of_kind(FACT)],
            "calculations": [i.id for i in self.of_kind(CALCULATION)],
            "sourced": [i.id for i in self.of_kind(SOURCED)],
            "interpretations": [i.id for i in self.of_kind(INTERPRETATION)],
            "assumptions": [i.id for i in self.of_kind(ASSUMPTION)],
            "recommendations": [],
            "recommendations_status": DEFERRED_NOTE,
            "material_findings": [i.id for i in self.material()],
            "evidence": [s.as_instruction_safe_dict() for s in self._evidence_sets],
            "candidate_claims": self.candidate_claims,
            "conflicts": [c.as_dict() for c in self._conflicts],
            "limitations": limitations_mod.as_dicts(self._limitations),
            "confidence": assessment.as_dict(),
            "provenance_index": self.provenance_index(),
            "summary": self.summary(),
            "notes": list(self.notes),
            "runs": [dict(record) for record in self._runs.values()],
            "run_bindings": dict(sorted(self._run_of.items())),
        }

    def to_json(self, indent=None):
        """Deterministic serialisation: sorted keys, stable order, JSON-safe throughout."""
        return json.dumps(self.as_dict(), sort_keys=True, indent=indent, default=str)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __repr__(self):
        return "SynthesisSet(%s: %d items, %d conflicts, %d limitations)" % (
            self.synthesis_type, len(self._items), len(self._conflicts),
            len(self._limitations))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provenance_kind_for(analysis_set):
    """Which provenance kind an analysis set's findings are referenced under."""
    from ..anomaly import contract as anomaly_contract
    from ..forecast import contract as forecast_contract
    if isinstance(analysis_set, forecast_contract.ForecastSet):
        return P_FORECAST
    if isinstance(analysis_set, anomaly_contract.AnomalySet):
        return P_ANOMALY
    return P_FINDING


#: Fields only a class-7 recommendation record carries (ADR-0031). A retrieved candidate claim
#: never has one, so their presence identifies a recommendation however it was relabelled.
_RECOMMENDATION_ONLY_FIELDS = ("recommendation_id", "issued_by", "action", "rationale",
                               "expected_benefit", "risks", "dependencies")

#: A decision package and its parts are advice built from this layer's statements too, and never
#: re-enter it (ADR-0032, security constraint 7). These fields occur only in a package or a part.
_DECISION_PACKAGE_ANALYSIS = "decision_support"
_DECISION_PACKAGE_ONLY_FIELDS = ("decision_question", "lifecycle", "option_id", "criterion_id",
                                 "tradeoff_id", "risk_id", "outcome_id", "preferred_option",
                                 "preference_basis", "no_preference_reason", "divergences",
                                 "next_steps", "option_ids", "criterion_ids", "assumption_ids",
                                 "recommendation_ids", "referenced_by", "addresses")
#: The origins a package gives the user's own framing (question, objective, constraint, option).
_DECISION_FRAMING_ORIGINS = ("user", "status_quo")

#: An executive report and every section or entry of one is assembled from this layer's own
#: statements and the results built on them, and never re-enters it (ADR-0033 section 14). These
#: fields occur only in a report, a section, a serialised statement view, a KPI row or a SWOT
#: point - never in a candidate claim a retrieval produced.
_EXECUTIVE_REPORT_ANALYSIS = "executive_report"
_EXECUTIVE_REPORT_ONLY_FIELDS = ("report_id", "section_order", "sections", "reporting_frame",
                                 "executive_summary", "kpi_scorecard", "findings", "anomalies",
                                 "outlook", "evidence_and_uncertainty",
                                 "decisions_for_the_reader", "material_statements",
                                 "synthesis_id", "statement_detail", "synthesis_digest",
                                 "package_digest",
                                 "kpi_id", "point_id", "quadrants", "lifecycle_label",
                                 "human_decision")


#: A verification result, each check and finding in it, and every final artifact carrying a
#: verification record are statements about BusinessOps's own artifacts. None re-enters the
#: evidence those artifacts were built from (ADR-0034 section 14, ADR-0035 section 7).
_VERIFICATION_ANALYSIS = "verification"
_VERIFICATION_ONLY_FIELDS = ("verification_id", "verified_by", "verification_record",
                             "finding_id", "check_id", "request_id", "record_id",
                             "finalisation_permitted", "recomputation", "subject_digest")


#: A data profile and every source, dataset, column, candidate and applicability entry of one
#: describe files, not the business, and never enter synthesis (ADR-0036 section 11).
_DATA_PROFILE_ANALYSIS = "data_profile"
_DATA_PROFILE_ONLY_FIELDS = ("profile_id", "source_ref", "dataset_ref", "column_ref",
                             "key_candidates", "relationships", "applicability",
                             # a command applicability entry and a key overlap entry carry
                             # neither a ref field nor a ref-shaped value, so their own fields
                             "required_roles", "overlap_rate")
#: A profile's own identifiers. A relationship or limitation entry carries them as values rather
#: than under a profile-only field name, so the values are recognised too.
_DATA_PROFILE_REF = re.compile(r"^(dpr|src|dst|col)-[0-9a-f]{12}$")
#: The bases a profile fact carries beside `examined`; no candidate claim has that shape.
_DATA_PROFILE_BASES = ("observed", "calculated", "inferred")


def _is_data_profile(record):
    """Whether a record is a data profile, a part of one, or dressed as either.

    Nested records and lists are examined too: a wrapper around profile entries (the
    applicability section holds its command and KPI entries one level down) is still a profile.
    """
    if isinstance(record, list):
        return any(_is_data_profile(item) for item in record)
    if not isinstance(record, dict):
        return isinstance(record, str) and bool(_DATA_PROFILE_REF.match(record.strip()))
    if str(record.get("analysis", "")).strip().lower() == _DATA_PROFILE_ANALYSIS:
        return True
    if any(field in record for field in _DATA_PROFILE_ONLY_FIELDS):
        return True
    if "examined" in record and str(record.get("basis", "")).strip().lower() in _DATA_PROFILE_BASES:
        return True
    return any(_is_data_profile(value) for value in record.values())


#: Connector catalogues, resolutions and briefs, and every entry of one, describe a connected
#: system's structure and never enter synthesis; nor does any class-2 claim, because no M12-B
#: path can produce a legitimate one (ADR-0037 section I). Recognised by shape, like the profile
#: above, so this layer imports nothing from `bops.connectors`.
_CONNECTOR_ANALYSES = ("connector_catalogue", "connector_resolution")
_CONNECTOR_ONLY_FIELDS = ("catalogue_id", "connector_id", "capability_placeholder",
                          "related_object", "dropped_keys", "object_types", "object_type",
                          "server_key", "tool_name")
#: A dropped-key note (`key`, `reason`) and a limitation (`code`, `subject`) carry no
#: connector-only field name, so their closed values identify them.
_CONNECTOR_NOTE_REASONS = ("authority", "privacy_restricted", "not_allowlisted", "length_bound",
                           "out_of_scope")
_CONNECTOR_CODES = (
    "connector_not_configured", "ambiguous_connector", "capability_unsupported",
    "binding_mismatch", "connector_unavailable", "connector_not_authorized",
    "authentication_failure", "authorization_failure", "timeout", "tool_failure",
    "malformed_response", "operation_unknown", "stale_metadata", "metadata_conflict",
    "external_content_unavailable", "privacy_restricted", "insufficient_data", "request_invalid",
    "blocked_prerequisite")
#: Catalogue and operation ids carried as values rather than under a connector-only field.
_CONNECTOR_REF = re.compile(r"^(cat-[0-9a-f]{12}|cop-[0-9a-f]{24})$")
#: The basis the catalogue engine sets on every entry; no candidate claim carries it.
_CONNECTOR_BASIS = "relayed"
_CONNECTED_CLASS_NAME = "connected-system data"


def _is_connector_material(record):
    """Whether a record is connector material, a part of it, or a class-2 claim, however dressed.

    Nested records and lists are examined too, so a wrapper around catalogue entries is still a
    catalogue.
    """
    if isinstance(record, list):
        return any(_is_connector_material(item) for item in record)
    if not isinstance(record, dict):
        return isinstance(record, str) and bool(_CONNECTOR_REF.match(record.strip()))
    if str(record.get("analysis", "")).strip().lower() in _CONNECTOR_ANALYSES:
        return True
    if str(record.get("protocol", "")).strip().lower().startswith("bops.connector."):
        return True
    if any(field in record for field in _CONNECTOR_ONLY_FIELDS):
        return True
    if str(record.get("basis", "")).strip().lower() == _CONNECTOR_BASIS:
        return True
    if "key" in record and str(record.get("reason", "")).strip() in _CONNECTOR_NOTE_REASONS:
        return True
    if "subject" in record and str(record.get("code", "")).strip() in _CONNECTOR_CODES:
        return True
    for key in ("class", "provenance_class", "evidence_class"):
        if str(record.get(key, "")).strip() == str(evidence_mod.CONNECTED_DATA):
            return True
    if str(record.get("class_name", "")).strip().lower() == _CONNECTED_CLASS_NAME:
        return True
    return any(_is_connector_material(value) for value in record.values())


def _is_recommendation(record):
    """Whether a record is, or is dressed as, a class-7 recommendation.

    Checked on every spelling a serialised recommendation can take - the ledger's `class` and
    `label`, the analytics `finding_type`, a synthesis-style `kind`, and the fields only a
    recommendation carries - so relabelling one of them does not smuggle the rest back in.
    """
    for key in ("class", "provenance_class", "evidence_class"):
        if str(record.get(key, "")).strip() == str(evidence_mod.RECOMMENDATION):
            return True
    for key in ("label", "kind", "finding_type", "class_name"):
        if str(record.get(key, "")).strip().upper() == analytics_contract.RECOMMENDATION:
            return True
    if str(record.get("analysis", "")).strip().lower() == _DECISION_PACKAGE_ANALYSIS:
        return True
    if str(record.get("origin", "")).strip().lower() in _DECISION_FRAMING_ORIGINS:
        return True
    if str(record.get("analysis", "")).strip().lower() in (_EXECUTIVE_REPORT_ANALYSIS,
                                                           _VERIFICATION_ANALYSIS):
        return True
    if str(record.get("verification", "")).strip().lower() == "verified":
        return True
    return any(field in record
               for field in _RECOMMENDATION_ONLY_FIELDS + _DECISION_PACKAGE_ONLY_FIELDS
               + _EXECUTIVE_REPORT_ONLY_FIELDS + _VERIFICATION_ONLY_FIELDS)


def _refuse_forged_tier(item):
    """Refuse an evidence item claiming a stronger tier than its own source supports.

    Ingestion already derives the tier locally, so anything that came through the scout
    path passes silently. What this catches is an item constructed directly - in a
    fixture, a test, or a future caller - carrying a tier its reference does not earn.
    A weaker tier than classification is left alone: conservatism is never the attack.
    """
    order = {"A": 3, "B": 2, "C": 1, "D": 0}
    local, basis, _inferred = sources_mod.classify_tier(item.reference, item.source)
    if order.get(item.source_tier, 0) > order.get(local, 0):
        raise SynthesisError(
            "evidence %s claims tier %s but its source (%s) classifies locally as tier "
            "%s (%s). Source tiers are derived from the source, never accepted from the "
            "item." % (item.id, item.source_tier, item.reference, local, basis))


def load(record):
    """Rebuild a synthesis set's statements from its serialised form.

    Deliberately partial: statements and their provenance come back, registries do not.
    A reloaded set can be read and audited; re-grading it requires the source objects
    again, which is the honest constraint rather than a gap.
    """
    if not isinstance(record, dict):
        raise SynthesisError("a synthesis result must be a record")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise SynthesisError(
            "unsupported synthesis schema version %r" % (record.get("schema_version"),))
    if not isinstance(record.get("items"), list):
        raise SynthesisError("a synthesis result must carry an items array")
    return [SynthesisItem.from_dict(entry) for entry in record["items"]]
