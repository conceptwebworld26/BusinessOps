# -*- coding: utf-8 -*-
"""M11 verification and finalisation (ADR-0034, amended by ADR-0035).

A draft `ExecutiveReportResult` or `DecisionResult` becomes `final` only when this module finds
that it faithfully and reproducibly represents what it is bound to. Nothing here decides whether
a recommendation is wise, a risk serious, a source true or a decision right: verification is an
integrity check, and a final artifact is verified for integrity, never approved.

**Three methods, never substituted** (ADR-0034 section 5):

* *source binding* - identity and digest of the set and every component, ids resolved through
  `grounding`, and registered KPIs and findings agreeing with the statements that cite them;
* *reproduction and textual equality* - each artifact rebuilt by the engine that owns it, from
  the inputs it retained, must equal the draft byte for byte; located checks then say where;
* *blind recomputation* (ADR-0035) - every engine-footed figure recomputed from its
  fingerprinted source in a separate process that never receives a claimed value.

**The blind boundary.** `issue_recomputation()` writes a sealed, content-addressed request under
`./.businessops/verification/` and returns only its id. The `bops-analysis-verifier` agent passes
that id to the one MCP operation `recompute` (`verification_server.py`), which calls
`recompute_request()` here: it re-hashes each source, reruns the command, and writes a
machine-only record of salted SHA-256 digests - never values. The operation returns only the
closed `bops.verifier.result/1` envelope. `verify()` re-derives the request from the draft, binds
the record to it and compares digests. No model receives a source, a path, a checked value or a
recomputed value, and no model decides any outcome.

**Lifecycle.** `verify()` returns a `VerificationResult`; only a `passed` one, for that exact
draft, still bound, lets `finalise()` return a final object holding the unedited draft beside it.
Every finding blocks. There is no severity, no warning tier, no confidence and no timestamp.
"""

import copy
import hashlib
import io
import json
import os
import re

from . import decision_support as decision_mod
from . import executive_report as report_mod
from . import jsonschema_mini
from . import strategy as strategy_mod
from . import swot as swot_mod
from .commands import runner as runner_mod
from .kpi import catalog as kpi_catalog
from .quality import contract as quality_contract
from .synthesis import contract as contract_mod
from .synthesis import grounding
from .synthesis import synthesis_set as set_mod

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "verification"
VERIFIED_BY = "bops-analysis-verifier"
EXECUTOR = "bops-analysis-verifier"
PASSED = "passed"
FAILED = "failed"
VERIFIED = "verified"
UNVERIFIED = "unverified"
DRAFT = "draft"
FINAL = "final"

SUBJECT_REPORT = "executive_report"
SUBJECT_PACKAGE = "decision_package"

REQUEST_PROTOCOL = "bops.verifier.request/1"
RECORD_PROTOCOL = "bops.verifier.record/1"
RESULT_PROTOCOL = "bops.verifier.result/1"
REQUEST_ID = re.compile(r"^rcq-[0-9a-f]{16}$")
RECORD_ID = re.compile(r"^rcr-[0-9a-f]{16}$")
VERIFICATION_ID = re.compile(r"^ver-[0-9a-f]{12}$")
ENV_DIRECTORY = "BOPS_VERIFICATION_DIR"

#: The closed set of codes the operation may return. No other text ever leaves it.
ERROR_CODES = ("request_id_invalid", "request_not_found", "request_invalid",
               "request_digest_mismatch", "record_conflict", "execution_error")

KPI_FIELDS = ("status", "value", "currency", "unit")
ANALYSIS_FIELDS = ("statement", "observed", "comparison", "change", "change_pct", "period",
                   "materiality")
#: The canonical form of an absent value in a digest: a NUL followed by `null`, which no engine
#: string can equal.
NULL_MARKER = "\x00null"
_SEPARATOR = "\x1f"

FINAL_REPORT_NOTE = (
    "Final report. The analysis verifier confirmed that this report faithfully and reproducibly "
    "assembles the artifacts it is bound to and that its figures recompute from their source. "
    "Final means verified for integrity. It does not mean that any recommendation was accepted, "
    "any option chosen, any decision made or approved, or any action authorised.")
FINAL_PACKAGE_NOTE = (
    "Final decision package. The analysis verifier confirmed that this package faithfully and "
    "reproducibly represents the evidence it is bound to and that its figures recompute from "
    "their source. Final means verified for integrity. It does not mean that any option was "
    "chosen, any decision made or approved, or any action authorised.")
HUMAN_DECISION = (
    "Verification checks integrity, not wisdom: it records no approval and makes no decision. "
    "Acting on anything in a final report or package - a system write, a message, an export or "
    "an overwrite - still needs a person's decision and explicit per-action approval, and "
    "financial transactions are prohibited.")
VERIFICATION_NOTE = (
    "Every check below is deterministic. Every finding blocks finalisation, and none carries a "
    "severity, a confidence or a figure: each names what was checked and how it compared.")

# -- methods, categories, outcomes, comparison codes -----------------------------------------

SOURCE_BINDING = "source_binding"
REPRODUCTION = "reproduction"
TEXTUAL_EQUALITY = "textual_equality"
RECOMPUTATION = "recomputation"
METHODS = (SOURCE_BINDING, REPRODUCTION, TEXTUAL_EQUALITY, RECOMPUTATION)

CATEGORIES = ("input_integrity", "binding_integrity", "synthesis_integrity",
              "reproduction_integrity", "figure_recomputation", "section_integrity",
              "content_preservation", "provenance_integrity", "lifecycle_integrity",
              "boundary_integrity", "schema_integrity")

OUTCOMES = ("passed", "failed", "not_applicable", "not_run")

OBSERVED_CODES = ("differs", "absent", "extra", "mismatched", "unreadable", "not_run",
                  "malformed", "unbound", "refused", "duplicate", "not_final", "unexpected",
                  "invalid", "unavailable") + ERROR_CODES

REPORT = "report"
PACKAGE = "package"
BOTH = (REPORT, PACKAGE)

#: The mandatory check catalogue, in execution and presentation order (ADR-0034 section 6 as
#: amended by ADR-0035 section 6). `(check_id, category, method, applies_to, message)`.
CATALOGUE = (
    ("input.genuine_draft", "input_integrity", SOURCE_BINDING, BOTH,
     "The subject is not an unedited draft built by its engine."),
    ("binding.synthesis", "binding_integrity", SOURCE_BINDING, BOTH,
     "The synthesis set is not the object and state the subject was bound to."),
    ("binding.strategy", "binding_integrity", SOURCE_BINDING, BOTH,
     "The strategy result is not bound to the set or has changed since binding."),
    ("binding.decision_packages", "binding_integrity", SOURCE_BINDING, (REPORT,),
     "A decision package is unbound, changed, duplicated or bound to a different strategy result."),
    ("binding.swot", "binding_integrity", REPRODUCTION, (REPORT,),
     "The SWOT record no longer reproduces the digest it was bound with."),
    ("binding.sources_record", "binding_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "The report's sources record disagrees with the components it holds."),
    ("synthesis.genuine_strict", "synthesis_integrity", SOURCE_BINDING, BOTH,
     "The synthesis set is not a genuine, strict, non-empty, fully graded set."),
    ("synthesis.quality_grade", "synthesis_integrity", SOURCE_BINDING, BOTH,
     "The synthesis set is declared CRITICAL quality."),
    ("synthesis.statement_ids", "synthesis_integrity", SOURCE_BINDING, BOTH,
     "A statement id does not resolve exactly once."),
    ("synthesis.registry_agreement", "synthesis_integrity", SOURCE_BINDING, BOTH,
     "A registered KPI or finding disagrees with the statement that cites it."),
    ("reproduction.swot", "reproduction_integrity", REPRODUCTION, (REPORT,),
     "The SWOT record is not what its placements produce over this set."),
    ("reproduction.strategy", "reproduction_integrity", REPRODUCTION, BOTH,
     "The strategy result is not what its proposals produce over this set."),
    ("reproduction.decision_package", "reproduction_integrity", REPRODUCTION, BOTH,
     "A decision package is not what its request produces over this set."),
    ("reproduction.report", "reproduction_integrity", REPRODUCTION, (REPORT,),
     "The report is not what its inputs produce over this set."),
    ("recomputation.request", "figure_recomputation", RECOMPUTATION, BOTH,
     "A headline figure has no recomputation basis, so no request can be issued for it."),
    ("recomputation.relay", "figure_recomputation", RECOMPUTATION, BOTH,
     "The relayed status envelope is absent, malformed, for another request, or failed."),
    ("recomputation.record", "figure_recomputation", RECOMPUTATION, BOTH,
     "The recomputation record is missing, altered, or bound to another request."),
    ("recomputation.source", "figure_recomputation", RECOMPUTATION, BOTH,
     "A source file no longer matches the SHA-256 recorded for its run."),
    ("recomputation.configuration", "figure_recomputation", RECOMPUTATION, BOTH,
     "The resolved configuration no longer matches the digest recorded for its run."),
    ("recomputation.execution", "figure_recomputation", RECOMPUTATION, BOTH,
     "A run could not be executed to completion."),
    ("recomputation.coverage", "figure_recomputation", RECOMPUTATION, BOTH,
     "A requested run, item or field is absent, or an unrequested one is present."),
    ("recomputation.kpi", "figure_recomputation", RECOMPUTATION, BOTH,
     "A recomputed KPI field differs from the draft."),
    ("recomputation.statement", "figure_recomputation", RECOMPUTATION, BOTH,
     "A recomputed statement field differs from the draft."),
    ("section.set", "section_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "The report does not hold exactly the eleven sections."),
    ("section.order", "section_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "The sections are not in the fixed order."),
    ("section.status", "section_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "A section status or reason is not one that section permits."),
    ("section.availability", "section_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "The summary's availability list disagrees with the sections."),
    ("content.statements", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "A shown statement differs from the set, or is out of set order."),
    ("content.summary", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "The executive summary is not the rule selection over the set."),
    ("content.kpi", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "The KPI scorecard differs from the registered KPIs or their catalogue order."),
    ("content.anomalies", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "An anomaly entry differs from its resolved finding or lacks its caveats."),
    ("content.strategy", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "The strategy section differs from the strategy result."),
    ("content.swot", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "The SWOT section differs from the SWOT record."),
    ("content.decision_packages", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "A decision package differs from its source or is out of supplied order."),
    ("content.evidence_and_uncertainty", "content_preservation", TEXTUAL_EQUALITY, (REPORT,),
     "Evidence and uncertainty differ from the set and the components."),
    ("provenance.evidence_kinds", "provenance_integrity", TEXTUAL_EQUALITY, BOTH,
     "A statement appears under a kind or block it may not."),
    ("provenance.owned_content", "provenance_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "Something that is not a statement of the set is shown as one."),
    ("provenance.framing", "provenance_integrity", TEXTUAL_EQUALITY, BOTH,
     "User framing is not verbatim or not labelled as the user's."),
    ("provenance.external_trust", "provenance_integrity", TEXTUAL_EQUALITY, BOTH,
     "External content is not labelled untrusted."),
    ("provenance.outlook", "provenance_integrity", TEXTUAL_EQUALITY, (REPORT,),
     "The outlook is not the fixed not-available state."),
    ("lifecycle.draft_input", "lifecycle_integrity", SOURCE_BINDING, BOTH,
     "The subject's lifecycle fields are not the draft constants."),
    ("lifecycle.packages_final", "lifecycle_integrity", SOURCE_BINDING, (REPORT,),
     "The report includes a decision package that is not final and still bound."),
    ("boundary.fixed_text", "boundary_integrity", TEXTUAL_EQUALITY, BOTH,
     "An engine-owned sentence differs from its constant."),
    ("boundary.forbidden_fields", "boundary_integrity", TEXTUAL_EQUALITY, BOTH,
     "A score, rank, weight, priority, severity, likelihood, rating, target, owner or execution "
     "field is present."),
    ("schema.subject", "schema_integrity", TEXTUAL_EQUALITY, BOTH,
     "The subject does not validate against its closed schema."),
    ("schema.components", "schema_integrity", TEXTUAL_EQUALITY, BOTH,
     "A component does not validate against its closed schema."),
)
CHECK_IDS = tuple(entry[0] for entry in CATALOGUE)
_CATALOGUE_INDEX = dict((entry[0], position) for position, entry in enumerate(CATALOGUE))

_SCHEMAS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "schemas")

_FORBIDDEN_KEY_PARTS = frozenset(("score", "scores", "weight", "weights", "rank", "ranking",
                                  "priority", "priorities", "severity", "likelihood", "rating",
                                  "ratings", "color", "colour", "target", "targets", "owner",
                                  "owners", "due", "execution", "executed"))

#: The statuses each section permits, and the fixed reason each non-included status carries.
_SECTION_STATUS = {
    report_mod.REPORTING_FRAME: {report_mod.INCLUDED: None},
    report_mod.EXECUTIVE_SUMMARY: {report_mod.INCLUDED: None},
    report_mod.KPI_SCORECARD: {report_mod.INCLUDED: None,
                               report_mod.NOT_AVAILABLE: report_mod.REASON_NO_KPI},
    report_mod.FINDINGS: {report_mod.INCLUDED: None,
                          report_mod.EMPTY: report_mod.REASON_NO_FINDINGS},
    report_mod.ANOMALIES: {report_mod.INCLUDED: None,
                           report_mod.EMPTY: report_mod.REASON_ANOMALY_NOT_READABLE,
                           report_mod.NOT_AVAILABLE: report_mod.REASON_NO_ANOMALY},
    report_mod.OUTLOOK: {report_mod.NOT_AVAILABLE: report_mod.REASON_NO_FORECAST},
    report_mod.SWOT: {report_mod.INCLUDED: None, report_mod.EMPTY: report_mod.REASON_EMPTY_SWOT,
                      report_mod.NOT_SUPPLIED: report_mod.REASON_NO_SWOT},
    report_mod.STRATEGY_RECOMMENDATIONS: {
        report_mod.INCLUDED: None, report_mod.EMPTY: report_mod.REASON_EMPTY_STRATEGY,
        report_mod.NOT_SUPPLIED: report_mod.REASON_NO_STRATEGY},
    report_mod.DECISION_SUPPORT: {report_mod.INCLUDED: None,
                                  report_mod.NOT_SUPPLIED: report_mod.REASON_NO_DECISION},
    report_mod.EVIDENCE_AND_UNCERTAINTY: {report_mod.INCLUDED: None},
    report_mod.DECISIONS_FOR_THE_READER: {report_mod.INCLUDED: None},
}

_BUILD_TOKEN = object()


class VerificationError(contract_mod.SynthesisError):
    """An input is not a genuine draft, or finalisation is not permitted. Nothing is emitted."""


# ---------------------------------------------------------------------------
# Canonical forms, digests and the working directory
# ---------------------------------------------------------------------------

def _sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value):
    """The exact string a figure is compared by: the engine's own `str()`, never normalised."""
    return NULL_MARKER if value is None else str(value)


def field_digest(request_id, run_id, kind, item_id, field, value):
    """Salted SHA-256 of one field's canonical string (ADR-0035 section 5). Not a secrecy tool."""
    seed = _SEPARATOR.join((request_id, run_id, kind, str(item_id), field, canonical(value)))
    return "sha256:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def verification_directory():
    """`./.businessops/verification/`, resolved from the working directory like Business Context."""
    override = os.environ.get(ENV_DIRECTORY)
    if override:
        return os.path.abspath(override)
    return os.path.join(os.getcwd(), ".businessops", "verification")


def _request_path(request_id):
    return os.path.join(verification_directory(), "requests", request_id + ".json")


def _record_path(record_id):
    return os.path.join(verification_directory(), "records", record_id + ".json")


def _write_exclusive(path, data):
    """Create `path` with `data`; an existing file must already hold exactly `data`."""
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    try:
        with io.open(path, "xb") as handle:
            handle.write(data)
        return True
    except (OSError, IOError):
        try:
            with io.open(path, "rb") as handle:
                return handle.read() == data
        except (OSError, IOError):
            return False


def _content_address(prefix, record, length):
    body = dict((k, v) for k, v in record.items() if k not in ("request_id", "record_id"))
    seed = runner_mod.canonical_json(body)
    return prefix + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:length]


def _remove_quietly(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------

def _subject_kind(subject):
    if type(subject) is report_mod.ExecutiveReportResult:
        return REPORT
    if type(subject) is decision_mod.DecisionResult:
        return PACKAGE
    if type(subject) in (FinalExecutiveReportResult, FinalDecisionResult):
        raise VerificationError(
            "this artifact is already final. A final artifact is never verified again or "
            "downgraded; verify its draft, which stays independently verifiable")
    raise VerificationError(
        "verification takes the draft ExecutiveReportResult or DecisionResult object its engine "
        "built. A serialised copy, a dict, a look-alike or any caller-supplied result, finding, "
        "lifecycle, confidence, trust or value is not accepted")


def _report_json(report):
    """The report's canonical serialisation without the binding check `to_json()` applies."""
    return json.dumps(report._report, indent=None, default=str)


def _package_json(package):
    try:
        return package.to_json()
    except (decision_mod.DecisionSupportError, contract_mod.SynthesisError):
        return None


def _subject_digest(kind, subject):
    text = _report_json(subject) if kind == REPORT else _package_json(subject)
    return None if text is None else _sha256_text(text)


def _draft_of(package):
    return package.draft if type(package) is FinalDecisionResult else package


# ---------------------------------------------------------------------------
# The recomputation plan: what is recomputed, from which run
# ---------------------------------------------------------------------------

_ENGINE_KINDS = (contract_mod.P_FINDING, contract_mod.P_ANOMALY)


def _engine_ref(item):
    """`("kpi"|"analysis", provenance kind, id)` for an engine-footed statement, or `None`.

    Only a `FACT` or `CALCULATION` is an engine's own figure. An interpretation carries its
    supports' references but its text is a reading, verified by grounding and reproduction.
    """
    if item.kind not in contract_mod.INTERNALLY_FOOTED_KINDS:
        return None
    for ref in item.provenance:
        if ref.kind == contract_mod.P_KPI and ref.ref_id:
            return ("kpi", ref.kind, str(ref.ref_id))
    for ref in item.provenance:
        if ref.kind in _ENGINE_KINDS and ref.ref_id:
            return ("analysis", ref.kind, str(ref.ref_id))
    return None


class _Plan(object):
    """Every headline figure of a subject, the run it comes from, and its expected strings."""

    def __init__(self):
        self.items = []          # (run_id, kind, id, fields, component, location)
        self.expected = {}       # (run_id, kind, id, field) -> value
        self.missing = []        # (component, location)
        self.runs = []           # run records in registration order
        self.request = None
        self.request_id = None

    @property
    def required(self):
        return bool(self.items or self.missing)


def _plan(kind, subject, synthesis):
    plan = _Plan()
    seen = set()

    def add(item_kind, provenance_kind, item_id, values, component, location):
        key = (item_kind, item_id)
        if key in seen:
            return
        seen.add(key)
        run = synthesis.run_for(provenance_kind, item_id)
        if run is None:
            plan.missing.append((component, location))
            return
        fields = KPI_FIELDS if item_kind == "kpi" else ANALYSIS_FIELDS
        plan.items.append((run["run_id"], item_kind, item_id, fields, component, location))
        for field in fields:
            plan.expected[(run["run_id"], item_kind, item_id, field)] = values[field]

    def kpi_values(result):
        return {"status": result.status, "value": result.value, "currency": result.currency,
                "unit": result.unit}

    def analysis_values(item):
        return {"statement": item.statement, "observed": item.observed,
                "comparison": item.comparison, "change": item.change,
                "change_pct": item.change_pct, "period": item.period,
                "materiality": (item.materiality or {}).get("outcome")}

    if kind == REPORT:
        registered = dict((result.kpi_id, result) for result in synthesis.registered_kpis())
        order = [d.kpi_id for d in kpi_catalog.CATALOGUE if d.kpi_id in registered]
        order += sorted(k for k in registered if k not in order)
        for position, kpi_id in enumerate(order):
            add("kpi", contract_mod.P_KPI, kpi_id, kpi_values(registered[kpi_id]),
                {"kind": "kpi", "ref": kpi_id},
                "/sections/kpi_scorecard/rows/%d" % position)
        candidates = list(synthesis.items)
    else:
        cited = set(entry["synthesis_id"] for entry in subject.body["evidence"])
        candidates = [item for item in synthesis.items if item.id in cited]

    for item in candidates:
        ref = _engine_ref(item)
        if ref is None:
            continue
        item_kind, provenance_kind, item_id = ref
        component = {"kind": "statement", "ref": item.id}
        if item_kind == "kpi":
            result = synthesis.resolve_ref(contract_mod.ProvenanceRef(provenance_kind, item_id))
            if result is None:
                plan.missing.append((component, "/synthesis/%s" % item.id))
                continue
            add("kpi", provenance_kind, item_id, kpi_values(result), component,
                "/synthesis/%s" % item.id)
        else:
            add("analysis", provenance_kind, item_id, analysis_values(item), component,
                "/synthesis/%s" % item.id)

    if plan.missing or not plan.items:
        return plan
    used = []
    for record in synthesis.registered_runs():
        if any(run_id == record["run_id"] for run_id, *_rest in plan.items):
            used.append(record)
    plan.runs = used
    runs = []
    for record in used:
        runs.append({
            "run_id": record["run_id"], "command_id": record["command_id"],
            "source_path": record["source_path"], "source_sha256": record["source_sha256"],
            "run_arguments": record["run_arguments"], "config_digest": record["config_digest"],
            "items": [{"kind": item_kind, "id": item_id, "fields": list(fields)}
                      for run_id, item_kind, item_id, fields, _c, _l in plan.items
                      if run_id == record["run_id"]]})
    request = {"protocol": REQUEST_PROTOCOL, "runs": runs}
    plan.request_id = _content_address("rcq-", request, 16)
    plan.request = {"protocol": REQUEST_PROTOCOL, "request_id": plan.request_id, "runs": runs}
    return plan


def _request_bytes(request):
    return runner_mod.canonical_json(request).encode("utf-8")


def issue_recomputation(draft):
    """Write the sealed recomputation request for a draft; return its id, or `None`.

    `None` means the draft shows no engine-footed figure, so nothing is recomputed and no agent
    is dispatched. The id is the only thing that may be passed to `bops-analysis-verifier`.
    """
    kind = _subject_kind(draft)
    synthesis = draft.synthesis
    plan = _plan(kind, draft, synthesis)
    if plan.missing:
        raise VerificationError(
            "%d headline figure(s) have no recomputation basis - they entered the set outside "
            "the command path - so no request can be issued and the draft cannot be finalised"
            % len(plan.missing))
    if not plan.items:
        return None
    if not _write_exclusive(_request_path(plan.request_id), _request_bytes(plan.request)):
        raise VerificationError("a different request already holds this request id")
    return plan.request_id


# ---------------------------------------------------------------------------
# The fixed operation behind the `recompute` MCP tool (ADR-0035 section 3)
# ---------------------------------------------------------------------------

def envelope(request_id, status, record_id=None, error_code=None):
    """The only shape the operation returns. No value, count, hash, path or message."""
    if error_code is not None and error_code not in ERROR_CODES:
        error_code = "execution_error"
    return {"protocol": RESULT_PROTOCOL,
            "request_id": request_id if isinstance(request_id, str)
            and REQUEST_ID.match(request_id) else None,
            "status": status, "record_id": record_id, "error_code": error_code}


def valid_arguments(arguments):
    """True only for exactly `{"request_id": "rcq-<16 hex>"}`."""
    return (isinstance(arguments, dict) and set(arguments) == {"request_id"}
            and isinstance(arguments["request_id"], str)
            and REQUEST_ID.match(arguments["request_id"]) is not None)


def _closed_request(request):
    """Whether a parsed request has exactly the protocol shape; types checked, nothing else."""
    if not isinstance(request, dict) or set(request) != {"protocol", "request_id", "runs"}:
        return False
    if request["protocol"] != REQUEST_PROTOCOL or not isinstance(request["runs"], list):
        return False
    run_keys = {"run_id", "command_id", "source_path", "source_sha256", "run_arguments",
                "config_digest", "items"}
    for run in request["runs"]:
        if not isinstance(run, dict) or set(run) != run_keys or not isinstance(run["items"], list):
            return False
        if not isinstance(run["run_arguments"], dict):
            return False
        for item in run["items"]:
            if not isinstance(item, dict) or set(item) != {"kind", "id", "fields"}:
                return False
            allowed = KPI_FIELDS if item["kind"] == "kpi" else (
                ANALYSIS_FIELDS if item["kind"] == "analysis" else None)
            if allowed is None or not isinstance(item["fields"], list) \
                    or not set(item["fields"]) <= set(allowed):
                return False
    return True


def _recomputed_values(command_result, item):
    if item["kind"] == "kpi":
        result = command_result.kpis.get(item["id"])
        if result is None:
            return None
        return {"status": result.status, "value": result.value, "currency": result.currency,
                "unit": result.unit}
    for analysis in command_result.analyses.values():
        for finding in getattr(analysis, "findings", ()):
            if str(finding.analysis_id) == item["id"]:
                return {"statement": finding.statement, "observed": finding.observed,
                        "comparison": finding.comparison, "change": finding.change,
                        "change_pct": finding.change_pct, "period": finding.period,
                        "materiality": finding.materiality}
    return None


def recompute_request(arguments):
    """Execute one sealed request and write its record; return the closed envelope.

    Called by the `recompute` MCP tool with the tool's raw arguments. Everything it needs is
    resolved from the request file; nothing it returns carries a value, a path or a message.
    """
    if not valid_arguments(arguments):
        return envelope(None, FAILED, error_code="request_id_invalid")
    request_id = arguments["request_id"]
    try:
        directory = os.path.realpath(os.path.join(verification_directory(), "requests"))
        path = os.path.realpath(_request_path(request_id))
        if os.path.dirname(path) != directory or not os.path.isfile(path):
            return envelope(request_id, FAILED, error_code="request_not_found")
        with io.open(path, "rb") as handle:
            data = handle.read()
        try:
            request = json.loads(data.decode("utf-8"))
        except ValueError:
            return envelope(request_id, FAILED, error_code="request_invalid")
        if not _closed_request(request) or _request_bytes(request) != data:
            return envelope(request_id, FAILED, error_code="request_invalid")
        if request["request_id"] != request_id \
                or _content_address("rcq-", request, 16) != request_id:
            return envelope(request_id, FAILED, error_code="request_digest_mismatch")

        runs = []
        for run in request["runs"]:
            outcome = {"run_id": run["run_id"], "source_status": "unreadable",
                       "config_status": "not_checked", "run_status": "not_run", "items": []}
            runs.append(outcome)
            observed = runner_mod.source_sha256(run["source_path"])
            if observed is None:
                continue
            if observed != run["source_sha256"]:
                outcome["source_status"] = "mismatched"
                continue
            outcome["source_status"] = "matched"
            command_result = runner_mod.run(run["command_id"], source=run["source_path"],
                                            **dict(run["run_arguments"]))
            if command_result.config_digest is None or command_result.run_id is None:
                outcome["run_status"] = "unavailable"
                continue
            if command_result.config_digest != run["config_digest"]:
                outcome["config_status"] = "mismatched"
                continue
            outcome["config_status"] = "matched"
            if command_result.run_id != run["run_id"]:
                outcome["run_status"] = "unavailable"
                continue
            outcome["run_status"] = "completed"
            for item in run["items"]:
                values = _recomputed_values(command_result, item)
                entry = {"kind": item["kind"], "id": item["id"],
                         "status": "absent" if values is None else "found", "digests": {}}
                if values is not None:
                    for field in item["fields"]:
                        entry["digests"][field] = field_digest(
                            request_id, run["run_id"], item["kind"], item["id"], field,
                            values[field])
                outcome["items"].append(entry)

        record = {"protocol": RECORD_PROTOCOL, "request_id": request_id,
                  "request_sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "runs": runs}
        record_id = _content_address("rcr-", record, 16)
        record = {"protocol": RECORD_PROTOCOL, "record_id": record_id, "request_id": request_id,
                  "request_sha256": record["request_sha256"], "runs": runs}
        if not _write_exclusive(_record_path(record_id), _request_bytes(record)):
            return envelope(request_id, FAILED, error_code="record_conflict")
        return envelope(request_id, "completed", record_id=record_id)
    except Exception:                                        # never text, never a traceback
        return envelope(request_id, FAILED, error_code="execution_error")


# ---------------------------------------------------------------------------
# Verification context
# ---------------------------------------------------------------------------

class _NotRun(Exception):
    """A check cannot run because an earlier check it depends on failed."""


class _Context(object):

    def __init__(self, kind, subject, relay):
        self.kind = kind
        self.subject = subject
        self.relay = relay
        self.synthesis = subject.synthesis
        self.digest = subject.synthesis_digest
        # Every comparison reads one normalised form: the report as its serialisation holds it.
        self.report = json.loads(_report_json(subject)) if kind == REPORT else None
        self.index = None
        self._rebuilt = False
        self.rebuilt = None
        self.plan = None
        self.record = None
        self.record_id = None
        self.usable_runs = {}
        self.stop_recomputation = False
        self.figures_checked = 0
        self.recomputation_status = "not_required"
        self.run_outcomes = []
        self.consumed = []

    # -- lazily computed shared views --------------------------------------

    def grounding_index(self):
        if self.index is None:
            self.index = grounding.index(self.synthesis)
        return self.index

    def rebuilt_report(self):
        """The report its own engine builds from the retained inputs, or `None` if refused."""
        if not self._rebuilt:
            self._rebuilt = True
            try:
                rebuilt = report_mod.build(
                    self.synthesis, self.subject.request,
                    strategy_result=self.subject.strategy_result, swot=self.subject.swot,
                    decision_results=self.subject.decision_results or None,
                    config=self.subject.config)
                self.rebuilt = json.loads(_report_json(rebuilt))
            except Exception:
                self.rebuilt = None
        return self.rebuilt


def _finding(check_id, component, location, expected, observed, section=None, position=0):
    return {"check_id": check_id, "component": component, "location": location,
            "expected": expected, "observed": observed, "_section": section,
            "_position": position}


def _section_of(location):
    if location and location.startswith("/sections/"):
        name = location.split("/")[2]
        if name in report_mod.SECTION_ORDER:
            return name
    return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _c_input(ctx):
    if ctx.kind == REPORT:
        report = ctx.report
        ok = (report.get("lifecycle") == DRAFT and report.get("verification") == UNVERIFIED
              and ctx.subject.lifecycle == DRAFT)
    else:
        ok = ctx.subject.lifecycle == DRAFT
    return [] if ok else [_finding("input.genuine_draft", {"kind": ctx.kind, "ref": None},
                                   "/lifecycle", "lifecycle:draft", "differs")]


def _c_binding_synthesis(ctx):
    found = []
    if strategy_mod.synthesis_digest(ctx.synthesis) != ctx.digest:
        found.append(_finding("binding.synthesis", {"kind": "synthesis_set", "ref": ctx.digest},
                              "/synthesis_digest", "binding:synthesis_digest", "mismatched"))
    if ctx.kind == REPORT and ctx.report.get("synthesis_digest") != ctx.digest:
        found.append(_finding("binding.synthesis", {"kind": "synthesis_set", "ref": ctx.digest},
                              "/synthesis_digest", "report:synthesis_digest", "differs"))
    return found


def _strategy_of(ctx):
    return (ctx.subject.strategy_result if ctx.kind == REPORT
            else ctx.subject.strategy_result)


def _c_binding_strategy(ctx):
    strategy = _strategy_of(ctx)
    if strategy is None:
        return None
    component = {"kind": "strategy_result", "ref": strategy.synthesis_digest}
    if not strategy.is_bound_to(ctx.synthesis):
        return [_finding("binding.strategy", component, None, "binding:strategy_result",
                         "unbound")]
    if ctx.kind == REPORT:
        try:
            digest = _sha256_text(strategy.to_json())
        except contract_mod.SynthesisError:
            digest = None
        if digest != ctx.subject._strategy_digest:
            return [_finding("binding.strategy", component, "/sources/strategy/digest",
                             "binding:strategy_digest", "mismatched")]
    return []


def _c_binding_packages(ctx):
    found, seen_ids, seen_digests = [], [], []
    strategy = ctx.subject.strategy_result
    for position, (package, digest) in enumerate(ctx.subject._packages):
        location = "/sections/decision_support/packages/%d" % position
        component = {"kind": "decision_package", "ref": digest}
        current = _package_json(package)
        if not package.is_bound_to(ctx.synthesis) or current is None:
            found.append(_finding("binding.decision_packages", component, location,
                                  "binding:package", "unbound", position=position))
        elif _sha256_text(current) != digest:
            found.append(_finding("binding.decision_packages", component, location,
                                  "binding:package_digest", "mismatched", position=position))
        if any(package is held for held in seen_ids) or digest in seen_digests:
            found.append(_finding("binding.decision_packages", component, location,
                                  "binding:package_unique", "duplicate", position=position))
        seen_ids.append(package)
        seen_digests.append(digest)
        if strategy is not None and package.strategy_result is not None \
                and package.strategy_result is not strategy:
            found.append(_finding("binding.decision_packages", component, location,
                                  "binding:package_strategy_result", "mismatched",
                                  position=position))
    return found


def _c_binding_swot(ctx):
    swot = ctx.subject._swot
    if swot is None:
        return []
    try:
        digest = report_mod._swot_digest(ctx.synthesis, swot)
    except contract_mod.SynthesisError:
        digest = None
    if digest != ctx.subject._swot_digest:
        return [_finding("binding.swot", {"kind": "swot", "ref": ctx.subject._swot_digest},
                         "/sources/swot/digest", "binding:swot_digest",
                         "refused" if digest is None else "mismatched")]
    return []


def _c_binding_sources(ctx):
    found = []
    sources = ctx.report.get("sources") or {}
    held = ctx.subject
    strategy = sources.get("strategy") or {}
    if bool(strategy.get("included")) != (held._strategy is not None):
        found.append(_finding("binding.sources_record", {"kind": "strategy_result", "ref": None},
                              "/sources/strategy/included", "held:strategy_result",
                              "absent" if strategy.get("included") else "extra"))
    elif strategy.get("digest") != held._strategy_digest:
        found.append(_finding("binding.sources_record",
                              {"kind": "strategy_result", "ref": held._strategy_digest},
                              "/sources/strategy/digest", "held:strategy_digest", "differs"))
    swot = sources.get("swot") or {}
    if bool(swot.get("included")) != (held._swot is not None):
        found.append(_finding("binding.sources_record", {"kind": "swot", "ref": None},
                              "/sources/swot/included", "held:swot",
                              "absent" if swot.get("included") else "extra"))
    elif swot.get("digest") != held._swot_digest:
        found.append(_finding("binding.sources_record", {"kind": "swot", "ref": held._swot_digest},
                              "/sources/swot/digest", "held:swot_digest", "differs"))
    listed = sources.get("decision_packages") or []
    digests = [digest for _package, digest in held._packages]
    if len(listed) != len(digests):
        found.append(_finding("binding.sources_record", {"kind": "decision_package", "ref": None},
                              "/sources/decision_packages", "held:decision_packages",
                              "absent" if len(listed) > len(digests) else "extra"))
    else:
        for position, (entry, digest) in enumerate(zip(listed, digests)):
            if entry.get("digest") != digest:
                found.append(_finding("binding.sources_record",
                                      {"kind": "decision_package", "ref": digest},
                                      "/sources/decision_packages/%d/digest" % position,
                                      "held:package_digest", "differs", position=position))
    return found


def _c_genuine_strict(ctx):
    try:
        grounding.genuine_set(ctx.synthesis)
    except grounding.GroundingError:
        return [_finding("synthesis.genuine_strict", {"kind": "synthesis_set", "ref": ctx.digest},
                         None, "synthesis:genuine_strict", "refused")]
    return []


def _c_quality(ctx):
    if ctx.synthesis.quality_grade == quality_contract.CRITICAL:
        return [_finding("synthesis.quality_grade", {"kind": "synthesis_set", "ref": ctx.digest},
                         "/quality_grade", "quality:not_critical", "differs")]
    return []


def _c_statement_ids(ctx):
    found = []
    index = ctx.grounding_index()
    for position, item in enumerate(ctx.synthesis.items):
        try:
            grounding.one(index, item.id)
        except grounding.GroundingError:
            found.append(_finding("synthesis.statement_ids", {"kind": "statement", "ref": item.id},
                                  "/synthesis/%s" % item.id, "synthesis:unique_id", "duplicate",
                                  position=position))
    return found


def _c_registry(ctx):
    found = []
    for position, item in enumerate(ctx.synthesis.items):
        ref = _engine_ref(item)
        if ref is None:
            continue
        item_kind, provenance_kind, item_id = ref
        registered = ctx.synthesis.resolve_ref(contract_mod.ProvenanceRef(provenance_kind,
                                                                          item_id))
        component = {"kind": "statement", "ref": item.id}
        location = "/synthesis/%s" % item.id
        if registered is None:
            found.append(_finding("synthesis.registry_agreement", component, location,
                                  "registry:%s/%s" % (item_kind, item_id), "absent",
                                  position=position))
            continue
        if item_kind == "kpi":
            pairs = (("observed", registered.value, item.observed),
                     ("currency", registered.currency, item.currency),
                     ("unit", registered.unit, item.unit))
        else:
            pairs = [("statement", registered.statement, item.statement),
                     ("observed", registered.observed, item.observed),
                     ("comparison", registered.comparison, item.comparison),
                     ("change", registered.change, item.change),
                     ("change_pct", registered.change_pct, item.change_pct),
                     ("materiality", registered.materiality,
                      (item.materiality or {}).get("outcome"))]
            if registered.period is not None:
                pairs.append(("period", registered.period, item.period))
        for field, left, right in pairs:
            if canonical(left) != canonical(right):
                found.append(_finding("synthesis.registry_agreement", component, location,
                                      "registry:%s/%s/%s" % (item_kind, item_id, field),
                                      "differs", position=position))
    return found


def _c_reproduction_swot(ctx):
    swot = ctx.subject._swot
    if swot is None:
        return []
    try:
        rebuilt = swot_mod.build(ctx.synthesis, report_mod._swot_placements(swot))
        same = swot_mod.to_json(rebuilt) == swot_mod.to_json(swot)
        observed = "differs"
    except Exception:
        same, observed = False, "refused"
    return [] if same else [_finding("reproduction.swot", {"kind": "swot", "ref": None},
                                     "/sections/swot/result", "rebuild:swot", observed)]


def _reproduce_strategy(ctx, strategy, location):
    try:
        rebuilt = strategy_mod.build(ctx.synthesis, strategy.proposals)
        same = rebuilt.to_json() == strategy.to_json()
        observed = "differs"
    except Exception:
        same, observed = False, "refused"
    if same:
        return []
    return [_finding("reproduction.strategy",
                     {"kind": "strategy_result", "ref": strategy.synthesis_digest}, location,
                     "rebuild:strategy_result", observed)]


def _c_reproduction_strategy(ctx):
    strategy = _strategy_of(ctx)
    if strategy is None:
        return None
    return _reproduce_strategy(ctx, strategy, "/sections/strategy_recommendations/result"
                               if ctx.kind == REPORT else "/body/guidance/recommendations")


def _reproduce_package(ctx, package, location, position=0):
    draft = _draft_of(package)
    try:
        rebuilt = decision_mod.build(ctx.synthesis, draft.request,
                                     strategy_result=draft.strategy_result, config=draft.config)
        same = rebuilt.to_json() == draft.to_json()
        observed = "differs"
    except Exception:
        same, observed = False, "refused"
    if same:
        return []
    return [_finding("reproduction.decision_package", {"kind": "decision_package",
                                                        "ref": _subject_digest(PACKAGE, draft)},
                     location, "rebuild:decision_package", observed, position=position)]


def _c_reproduction_package(ctx):
    if ctx.kind == PACKAGE:
        return _reproduce_package(ctx, ctx.subject, "/body")
    found = []
    for position, (package, _digest) in enumerate(ctx.subject._packages):
        found.extend(_reproduce_package(ctx, package,
                                        "/sections/decision_support/packages/%d" % position,
                                        position))
    return found if ctx.subject._packages else None


def _c_reproduction_report(ctx):
    rebuilt = ctx.rebuilt_report()
    if rebuilt is None:
        return [_finding("reproduction.report", {"kind": "executive_report",
                                                  "ref": ctx.report.get("report_id")},
                         None, "rebuild:report", "refused")]
    if json.dumps(rebuilt, indent=None, default=str) != _report_json(ctx.subject):
        observed = "differs"
        location = None
        if rebuilt.get("report_id") != ctx.report.get("report_id"):
            location = "/report_id"
        return [_finding("reproduction.report", {"kind": "executive_report",
                                                  "ref": ctx.report.get("report_id")},
                         location, "rebuild:report", observed)]
    return []


# -- recomputation -----------------------------------------------------------------------

def _c_request(ctx):
    ctx.plan = _plan(ctx.kind, ctx.subject, ctx.synthesis)
    if ctx.plan.missing:
        ctx.stop_recomputation = True
        ctx.recomputation_status = FAILED
        return [_finding("recomputation.request", component, location, "basis:run", "absent",
                         position=position)
                for position, (component, location) in enumerate(ctx.plan.missing)]
    if not ctx.plan.items:
        ctx.stop_recomputation = True
        return []
    ctx.consumed.append(_request_path(ctx.plan.request_id))
    return []


_FENCE = re.compile(r"^```(?:json)?[ \t]*\r?\n(?P<body>[^`]*?)\r?\n```$")


def _relay_text(relay):
    """The envelope text inside a relay: the text itself, or the body of one code fence.

    A model relaying the agent's reply may wrap it in a single markdown code fence. Removing that
    wrapper adds no trust - the body must still be exactly the closed envelope, and the record it
    names is bound to the request re-derived from the draft. Any other surrounding text is refused.
    """
    text = relay.strip()
    match = _FENCE.match(text)
    return match.group("body").strip() if match else text


def _require_recomputation(ctx):
    if ctx.plan is None or not ctx.plan.items:
        return False
    if ctx.stop_recomputation:
        raise _NotRun()
    return True


def _c_relay(ctx):
    if ctx.plan is not None and not ctx.plan.items and ctx.relay is not None \
            and not ctx.plan.missing:
        return [_finding("recomputation.relay", {"kind": "relay", "ref": None}, None,
                         "relay:none", "unexpected")]
    if not _require_recomputation(ctx):
        return None
    component = {"kind": "relay", "ref": ctx.plan.request_id}
    failure = None
    parsed = None
    if not isinstance(ctx.relay, str):
        failure = "absent" if ctx.relay is None else "malformed"
    else:
        try:
            parsed = json.loads(_relay_text(ctx.relay))
        except ValueError:
            failure = "malformed"
    if failure is None:
        keys = {"protocol", "request_id", "status", "record_id", "error_code"}
        if not isinstance(parsed, dict) or set(parsed) != keys \
                or parsed["protocol"] != RESULT_PROTOCOL \
                or parsed["status"] not in ("completed", FAILED) \
                or (parsed["error_code"] is not None and parsed["error_code"] not in ERROR_CODES):
            failure = "malformed"
        elif parsed["request_id"] != ctx.plan.request_id:
            failure = "mismatched"
        elif parsed["status"] == FAILED:
            failure = parsed["error_code"] or "execution_error"
        elif not isinstance(parsed["record_id"], str) or not RECORD_ID.match(parsed["record_id"]):
            failure = "malformed"
    if failure is not None:
        ctx.stop_recomputation = True
        ctx.recomputation_status = FAILED
        return [_finding("recomputation.relay", component, None, "relay:%s" % RESULT_PROTOCOL,
                         failure)]
    ctx.record_id = parsed["record_id"]
    return []


def _c_record(ctx):
    if not _require_recomputation(ctx):
        return None
    component = {"kind": "record", "ref": ctx.record_id}
    path = _record_path(ctx.record_id)
    ctx.consumed.append(path)
    try:
        with io.open(path, "rb") as handle:
            data = handle.read()
        record = json.loads(data.decode("utf-8"))
    except (OSError, IOError, ValueError):
        ctx.stop_recomputation = True
        ctx.recomputation_status = FAILED
        return [_finding("recomputation.record", component, None, "record:present", "absent")]
    expected_keys = {"protocol", "record_id", "request_id", "request_sha256", "runs"}
    request_sha = "sha256:" + hashlib.sha256(_request_bytes(ctx.plan.request)).hexdigest()
    failure = None
    if not isinstance(record, dict) or set(record) != expected_keys \
            or record["protocol"] != RECORD_PROTOCOL or not isinstance(record["runs"], list) \
            or _request_bytes(record) != data:
        failure = "malformed"
    elif record["record_id"] != ctx.record_id \
            or _content_address("rcr-", dict(record), 16) != ctx.record_id:
        failure = "mismatched"
    elif record["request_id"] != ctx.plan.request_id or record["request_sha256"] != request_sha:
        failure = "unbound"
    if failure is not None:
        ctx.stop_recomputation = True
        ctx.recomputation_status = FAILED
        return [_finding("recomputation.record", component, None, "record:bound_to_request",
                         failure)]
    ctx.record = record
    return []


def _record_runs(ctx):
    return [run for run in ctx.record["runs"] if isinstance(run, dict)]


def _c_run_status(ctx, check_id, field, good):
    if not _require_recomputation(ctx):
        return None
    found = []
    for position, run in enumerate(_record_runs(ctx)):
        run_id = run.get("run_id")
        if run_id in ctx.usable_runs and not ctx.usable_runs[run_id]:
            continue
        if run.get(field) != good:
            ctx.usable_runs[run_id] = False
            found.append(_finding(check_id, {"kind": "run", "ref": run_id}, None,
                                  "run:%s" % field, run.get(field) if run.get(field) in
                                  OBSERVED_CODES else "mismatched", position=position))
        else:
            ctx.usable_runs.setdefault(run_id, True)
    return found


def _c_source(ctx):
    return _c_run_status(ctx, "recomputation.source", "source_status", "matched")


def _c_configuration(ctx):
    return _c_run_status(ctx, "recomputation.configuration", "config_status", "matched")


def _c_execution(ctx):
    return _c_run_status(ctx, "recomputation.execution", "run_status", "completed")


def _c_coverage(ctx):
    if not _require_recomputation(ctx):
        return None
    found = []
    requested = dict((run["run_id"], run) for run in ctx.plan.request["runs"])
    listed = [run.get("run_id") for run in _record_runs(ctx)]
    for position, run_id in enumerate(requested):
        if listed.count(run_id) != 1:
            ctx.usable_runs[run_id] = False
            found.append(_finding("recomputation.coverage", {"kind": "run", "ref": run_id}, None,
                                  "coverage:run", "absent" if not listed.count(run_id)
                                  else "duplicate", position=position))
    for run_id in listed:
        if run_id not in requested:
            found.append(_finding("recomputation.coverage", {"kind": "run", "ref": run_id}, None,
                                  "coverage:run", "extra"))
    ctx.recomputed = {}
    for run in _record_runs(ctx):
        run_id = run.get("run_id")
        if run_id not in requested or not ctx.usable_runs.get(run_id):
            continue
        wanted = dict(((item["kind"], item["id"]), item["fields"])
                      for item in requested[run_id]["items"])
        got = {}
        for entry in run.get("items") or []:
            key = (entry.get("kind"), entry.get("id"))
            if key not in wanted or key in got:
                found.append(_finding("recomputation.coverage",
                                      {"kind": "item", "ref": "%s/%s" % key}, None,
                                      "coverage:item", "extra" if key not in wanted
                                      else "duplicate"))
                continue
            got[key] = entry
        for position, (key, fields) in enumerate(wanted.items()):
            entry = got.get(key)
            if entry is None or entry.get("status") != "found" \
                    or set((entry.get("digests") or {})) != set(fields):
                found.append(_finding("recomputation.coverage",
                                      {"kind": "item", "ref": "%s/%s" % key}, None,
                                      "coverage:item_fields", "absent", position=position))
                continue
            ctx.recomputed[(run_id,) + key] = entry["digests"]
    return found


def _c_compare(ctx, check_id, item_kind):
    if not _require_recomputation(ctx):
        return None
    if not any(ctx.usable_runs.values()):
        raise _NotRun()                      # nothing trustworthy to compare, so nothing passes
    found = []
    for position, (run_id, kind, item_id, fields, component, location) in \
            enumerate(ctx.plan.items):
        if kind != item_kind:
            continue
        digests = getattr(ctx, "recomputed", {}).get((run_id, kind, item_id))
        if digests is None:
            continue
        for field in fields:
            ctx.figures_checked += 1
            expected = field_digest(ctx.plan.request_id, run_id, kind, item_id, field,
                                    ctx.plan.expected[(run_id, kind, item_id, field)])
            if digests.get(field) != expected:
                found.append(_finding(check_id, component, location,
                                      "run:%s/%s:%s/%s" % (run_id, kind, item_id, field),
                                      "differs", section=_section_of(location),
                                      position=position))
    return found


def _c_kpi(ctx):
    return _c_compare(ctx, "recomputation.kpi", "kpi")


def _c_statement(ctx):
    found = _c_compare(ctx, "recomputation.statement", "analysis")
    if found is not None and ctx.recomputation_status != FAILED:
        ctx.recomputation_status = "completed"
    return found


# -- sections and content ------------------------------------------------------------------

def _sections(ctx):
    return ctx.report.get("sections") or {}


def _c_section_set(ctx):
    sections = _sections(ctx)
    names = set(sections) if isinstance(sections, dict) else set()
    found = []
    for name in report_mod.SECTION_ORDER:
        if name not in names:
            found.append(_finding("section.set", {"kind": "section", "ref": name},
                                  "/sections/%s" % name, "section:%s" % name, "absent",
                                  section=name))
    for name in sorted(names - set(report_mod.SECTION_ORDER)):
        found.append(_finding("section.set", {"kind": "section", "ref": name},
                              "/sections/%s" % name, "section:none", "extra"))
    return found


def _c_section_order(ctx):
    sections = _sections(ctx)
    if ctx.report.get("section_order") != list(report_mod.SECTION_ORDER) \
            or list(sections) != list(report_mod.SECTION_ORDER):
        return [_finding("section.order", {"kind": "section", "ref": None}, "/section_order",
                         "section_order:fixed", "differs")]
    return []


def _c_section_status(ctx):
    found = []
    for name, permitted in _SECTION_STATUS.items():
        section = _sections(ctx).get(name)
        if not isinstance(section, dict):
            continue
        status, reason = section.get("status"), section.get("reason")
        if status not in permitted or reason != permitted[status]:
            found.append(_finding("section.status", {"kind": "section", "ref": name},
                                  "/sections/%s/status" % name, "status:%s" % name,
                                  "invalid", section=name))
    return found


def _c_availability(ctx):
    summary = _sections(ctx).get(report_mod.EXECUTIVE_SUMMARY) or {}
    expected = [{"section": name, "status": (_sections(ctx).get(name) or {}).get("status")}
                for name in report_mod.AVAILABILITY_SECTIONS]
    if summary.get("availability") != expected:
        return [_finding("section.availability", {"kind": "section", "ref": "executive_summary"},
                         "/sections/executive_summary/availability", "availability:sections",
                         "differs", section=report_mod.EXECUTIVE_SUMMARY)]
    return []


def _walk_details(node, pointer):
    """Every `statement_detail` in the report, with its JSON pointer."""
    if isinstance(node, dict):
        for key, value in node.items():
            here = "%s/%s" % (pointer, key)
            if key == "statement_detail" and isinstance(value, dict):
                yield here, value
            else:
                for found in _walk_details(value, here):
                    yield found
    elif isinstance(node, list):
        for position, value in enumerate(node):
            for found in _walk_details(value, "%s/%d" % (pointer, position)):
                yield found


def _c_statements(ctx):
    found = []
    index = ctx.grounding_index()
    positions = dict((item.id, position) for position, item in enumerate(ctx.synthesis.items))
    last = {}
    for pointer, detail in _walk_details(_sections(ctx), "/sections"):
        synthesis_id = detail.get("synthesis_id")
        component = {"kind": "statement", "ref": synthesis_id}
        section = _section_of(pointer)
        if synthesis_id not in positions:
            found.append(_finding("content.statements", component, pointer,
                                  "synthesis:statement", "absent", section=section))
            continue
        position = positions[synthesis_id]
        try:
            current = strategy_mod.statement_detail(ctx.synthesis, index, position,
                                                    ctx.synthesis.items[position])
            current = json.loads(json.dumps(current, default=str))
        except Exception:
            current = None
        if current != detail:
            found.append(_finding("content.statements", component, pointer,
                                  "synthesis:%s" % synthesis_id, "differs", section=section,
                                  position=position))
        block = pointer.rsplit("/", 2)[0]
        if block in last and last[block] > position:
            found.append(_finding("content.statements", component, pointer, "order:set",
                                  "differs", section=section, position=position))
        last[block] = position
    return found


def _compare_section(ctx, check_id, name):
    rebuilt = ctx.rebuilt_report()
    if rebuilt is None:
        raise _NotRun()
    if (rebuilt.get("sections") or {}).get(name) != _sections(ctx).get(name):
        return [_finding(check_id, {"kind": "section", "ref": name}, "/sections/%s" % name,
                         "rebuild:section/%s" % name, "differs", section=name)]
    return []


def _c_summary(ctx):
    return _compare_section(ctx, "content.summary", report_mod.EXECUTIVE_SUMMARY)


def _c_kpi_section(ctx):
    found = _compare_section(ctx, "content.kpi", report_mod.KPI_SCORECARD)
    rows = (_sections(ctx).get(report_mod.KPI_SCORECARD) or {}).get("rows") or []
    ids = [row.get("kpi_id") for row in rows]
    catalogue = [d.kpi_id for d in kpi_catalog.CATALOGUE]
    known = [kpi_id for kpi_id in ids if kpi_id in catalogue]
    if known != sorted(known, key=catalogue.index):
        found.append(_finding("content.kpi", {"kind": "section", "ref": "kpi_scorecard"},
                              "/sections/kpi_scorecard/rows", "order:kpi_catalogue", "differs",
                              section=report_mod.KPI_SCORECARD))
    return found


def _c_anomalies(ctx):
    found = _compare_section(ctx, "content.anomalies", report_mod.ANOMALIES)
    by_id = dict((item.id, item) for item in ctx.synthesis.items)
    entries = (_sections(ctx).get(report_mod.ANOMALIES) or {}).get("statements") or []
    for position, entry in enumerate(entries):
        synthesis_id = (entry.get("statement_detail") or {}).get("synthesis_id")
        item = by_id.get(synthesis_id)
        if item is None or entry.get("caveats") != list(item.caveats):
            found.append(_finding("content.anomalies", {"kind": "statement", "ref": synthesis_id},
                                  "/sections/anomalies/statements/%d/caveats" % position,
                                  "synthesis:caveats", "differs",
                                  section=report_mod.ANOMALIES, position=position))
    return found


def _c_strategy_section(ctx):
    section = _sections(ctx).get(report_mod.STRATEGY_RECOMMENDATIONS) or {}
    strategy = ctx.subject.strategy_result
    try:
        expected = None if strategy is None else json.loads(json.dumps(strategy.as_dict(),
                                                                        default=str))
    except contract_mod.SynthesisError:
        expected = "unbound"
    if section.get("result") != expected:
        return [_finding("content.strategy", {"kind": "strategy_result", "ref": None},
                         "/sections/strategy_recommendations/result", "source:strategy_result",
                         "differs", section=report_mod.STRATEGY_RECOMMENDATIONS)]
    return []


def _c_swot_section(ctx):
    section = _sections(ctx).get(report_mod.SWOT) or {}
    held = ctx.subject._swot
    if section.get("result") != (None if held is None
                                 else json.loads(json.dumps(held, default=str))):
        return [_finding("content.swot", {"kind": "swot", "ref": None}, "/sections/swot/result",
                         "source:swot", "differs", section=report_mod.SWOT)]
    return []


def _c_packages_section(ctx):
    found = []
    entries = (_sections(ctx).get(report_mod.DECISION_SUPPORT) or {}).get("packages") or []
    held = ctx.subject._packages
    if len(entries) != len(held):
        return [_finding("content.decision_packages", {"kind": "decision_package", "ref": None},
                         "/sections/decision_support/packages", "source:decision_packages",
                         "differs", section=report_mod.DECISION_SUPPORT)]
    for position, (entry, (package, digest)) in enumerate(zip(entries, held)):
        current = _package_json(package)
        expected = None if current is None else json.loads(current)
        if entry.get("package") != expected or entry.get("package_digest") != digest:
            found.append(_finding("content.decision_packages",
                                  {"kind": "decision_package", "ref": digest},
                                  "/sections/decision_support/packages/%d" % position,
                                  "source:decision_package", "differs",
                                  section=report_mod.DECISION_SUPPORT, position=position))
    return found


def _c_evidence_section(ctx):
    found = _compare_section(ctx, "content.evidence_and_uncertainty",
                             report_mod.EVIDENCE_AND_UNCERTAINTY)
    section = _sections(ctx).get(report_mod.EVIDENCE_AND_UNCERTAINTY) or {}
    set_view = json.loads(ctx.synthesis.to_json())
    if section.get("conflicts") != set_view["conflicts"] \
            or section.get("limitations") != set_view["limitations"]:
        found.append(_finding("content.evidence_and_uncertainty",
                              {"kind": "synthesis_set", "ref": ctx.digest},
                              "/sections/evidence_and_uncertainty", "synthesis:conflicts_limits",
                              "differs", section=report_mod.EVIDENCE_AND_UNCERTAINTY))
    return found


# -- provenance, lifecycle, boundary, schema -----------------------------------------------

_EVIDENCE_KINDS = (contract_mod.FACT, contract_mod.CALCULATION, contract_mod.SOURCED)


def _c_evidence_kinds(ctx):
    found = []
    if ctx.kind == PACKAGE:
        for position, entry in enumerate(ctx.subject.body["evidence"]):
            if entry.get("kind") == contract_mod.ASSUMPTION:
                found.append(_finding("provenance.evidence_kinds",
                                      {"kind": "statement", "ref": entry.get("synthesis_id")},
                                      "/body/evidence/%d" % position, "kind:evidence",
                                      "differs", position=position))
        return found
    sections = _sections(ctx)
    rules = (
        ("/sections/findings/evidence", (sections.get("findings") or {}).get("evidence"),
         _EVIDENCE_KINDS, False),
        ("/sections/findings/interpretations",
         (sections.get("findings") or {}).get("interpretations"),
         (contract_mod.INTERPRETATION,), True),
    )
    for pointer, entries, kinds, needs_supports in rules:
        for position, entry in enumerate(entries or []):
            detail = entry.get("statement_detail") or {}
            if detail.get("kind") not in kinds or (needs_supports and not detail.get("supports")):
                found.append(_finding("provenance.evidence_kinds",
                                      {"kind": "statement", "ref": detail.get("synthesis_id")},
                                      "%s/%d" % (pointer, position), "kind:%s" % "|".join(kinds),
                                      "differs", section=_section_of(pointer), position=position))
    for pointer, detail in _walk_details(sections, "/sections"):
        if detail.get("kind") == contract_mod.ASSUMPTION:
            found.append(_finding("provenance.evidence_kinds",
                                  {"kind": "statement", "ref": detail.get("synthesis_id")},
                                  pointer, "kind:not_assumption", "differs",
                                  section=_section_of(pointer)))
    uncertainty = sections.get("evidence_and_uncertainty") or {}
    for position, entry in enumerate(uncertainty.get("assumptions") or []):
        if entry.get("kind") != contract_mod.ASSUMPTION:
            found.append(_finding("provenance.evidence_kinds",
                                  {"kind": "statement", "ref": entry.get("synthesis_id")},
                                  "/sections/evidence_and_uncertainty/assumptions/%d" % position,
                                  "kind:ASSUMPTION", "differs",
                                  section="evidence_and_uncertainty", position=position))
    return found


def _c_owned_content(ctx):
    found = []
    statements = dict((item.id, item.statement) for item in ctx.synthesis.items)
    strategy = ctx.subject.strategy_result
    record_ids = set()
    if strategy is not None:
        record_ids = set(r["recommendation_id"] for r in strategy.recommendations)
    for pointer, detail in _walk_details(_sections(ctx), "/sections"):
        synthesis_id = detail.get("synthesis_id")
        if synthesis_id in record_ids or statements.get(synthesis_id) != detail.get("statement"):
            found.append(_finding("provenance.owned_content",
                                  {"kind": "statement", "ref": synthesis_id}, pointer,
                                  "synthesis:owned_statement", "differs",
                                  section=_section_of(pointer)))
    return found


def _c_framing(ctx):
    if ctx.kind == PACKAGE:
        request = ctx.subject.request or {}
        question = ctx.subject.body["decision_question"]
        if question.get("text") != request.get("decision_question") \
                or question.get("origin") != decision_mod.USER:
            return [_finding("provenance.framing", {"kind": "framing", "ref": "decision_question"},
                             "/body/decision_question", "framing:user_verbatim", "differs")]
        return []
    frame = _sections(ctx).get(report_mod.REPORTING_FRAME) or {}
    try:
        expected = report_mod._framing(ctx.subject.request)
    except contract_mod.SynthesisError:
        expected = None
    if frame.get("framing") != expected:
        return [_finding("provenance.framing", {"kind": "framing", "ref": None},
                         "/sections/reporting_frame/framing", "framing:user_verbatim", "differs",
                         section=report_mod.REPORTING_FRAME)]
    return []


def _c_external_trust(ctx):
    found = []
    record = ctx.report if ctx.kind == REPORT else json.loads(_package_json(ctx.subject) or "{}")
    if record.get("trust_statement") != set_mod.TRUST_STATEMENT:
        found.append(_finding("provenance.external_trust", {"kind": ctx.kind, "ref": None},
                              "/trust_statement", "text:trust_statement", "differs"))
    root = _sections(ctx) if ctx.kind == REPORT else record.get("body") or {}
    for pointer, detail in _walk_details(root, "/sections" if ctx.kind == REPORT else "/body"):
        if detail.get("kind") == contract_mod.SOURCED and detail.get("trust") != "untrusted":
            found.append(_finding("provenance.external_trust",
                                  {"kind": "statement", "ref": detail.get("synthesis_id")},
                                  pointer, "trust:untrusted", "differs",
                                  section=_section_of(pointer)))
    return found


def _c_outlook(ctx):
    expected = {"status": report_mod.NOT_AVAILABLE, "reason": report_mod.REASON_NO_FORECAST,
                "statements": []}
    if _sections(ctx).get(report_mod.OUTLOOK) != expected:
        return [_finding("provenance.outlook", {"kind": "section", "ref": "outlook"},
                         "/sections/outlook", "outlook:not_available", "differs",
                         section=report_mod.OUTLOOK)]
    return []


def _c_draft_input(ctx):
    found = []
    if ctx.kind == REPORT:
        frame = _sections(ctx).get(report_mod.REPORTING_FRAME) or {}
        for pointer, holder in (("", ctx.report), ("/sections/reporting_frame", frame)):
            if holder.get("lifecycle") != DRAFT or holder.get("verification") != UNVERIFIED \
                    or holder.get("lifecycle_note") != report_mod.LIFECYCLE_NOTE:
                found.append(_finding("lifecycle.draft_input", {"kind": "executive_report",
                                                                 "ref": ctx.report.get("report_id")},
                                      pointer + "/lifecycle", "lifecycle:draft", "differs",
                                      section=_section_of(pointer)))
        return found
    record = _package_json(ctx.subject)
    record = json.loads(record) if record else {}
    if record and (record.get("lifecycle") != DRAFT or record.get("verification") != UNVERIFIED
                   or record.get("lifecycle_note") != decision_mod.LIFECYCLE_NOTE):
        found.append(_finding("lifecycle.draft_input", {"kind": "decision_package", "ref": None},
                              "/lifecycle", "lifecycle:draft", "differs"))
    return found


def _c_packages_final(ctx):
    found = []
    for position, (package, digest) in enumerate(ctx.subject._packages):
        location = "/sections/decision_support/packages/%d" % position
        component = {"kind": "decision_package", "ref": digest}
        if type(package) is not FinalDecisionResult:
            found.append(_finding("lifecycle.packages_final", component, location,
                                  "lifecycle:final", "not_final",
                                  section=report_mod.DECISION_SUPPORT, position=position))
        elif not package.is_bound_to(ctx.synthesis):
            found.append(_finding("lifecycle.packages_final", component, location,
                                  "lifecycle:final_bound", "unbound",
                                  section=report_mod.DECISION_SUPPORT, position=position))
    return found


def _c_fixed_text(ctx):
    found = []
    if ctx.kind == REPORT:
        reader = _sections(ctx).get(report_mod.DECISIONS_FOR_THE_READER) or {}
        frame = _sections(ctx).get(report_mod.REPORTING_FRAME) or {}
        pairs = (("/human_decision", ctx.report.get("human_decision"), report_mod.HUMAN_DECISION),
                 ("/order_note", ctx.report.get("order_note"), report_mod.ORDER_NOTE),
                 ("/sections/decisions_for_the_reader/human_decision",
                  reader.get("human_decision"), report_mod.HUMAN_DECISION),
                 ("/sections/decisions_for_the_reader/no_decision_recorded",
                  reader.get("no_decision_recorded"), report_mod.NO_DECISION_RECORDED))
        if frame.get("quality_warning") is not None:
            pairs += (("/sections/reporting_frame/quality_warning",
                       frame.get("quality_warning"), report_mod.QUALITY_WARNING),)
    else:
        record = json.loads(_package_json(ctx.subject) or "{}")
        if not record:
            return []
        pairs = (("/human_decision", record.get("human_decision"), decision_mod.HUMAN_DECISION),
                 ("/order_note", record.get("order_note"), decision_mod.ORDER_NOTE))
    for pointer, actual, expected in pairs:
        if actual != expected:
            found.append(_finding("boundary.fixed_text", {"kind": ctx.kind, "ref": None}, pointer,
                                  "text:%s" % pointer.rsplit("/", 1)[-1], "differs",
                                  section=_section_of(pointer)))
    return found


def _forbidden_keys(node, pointer):
    if isinstance(node, dict):
        for key, value in node.items():
            here = "%s/%s" % (pointer, key)
            if key != "kpi_scorecard" and set(str(key).lower().split("_")) & _FORBIDDEN_KEY_PARTS:
                yield here
            for found in _forbidden_keys(value, here):
                yield found
    elif isinstance(node, list):
        for position, value in enumerate(node):
            for found in _forbidden_keys(value, "%s/%d" % (pointer, position)):
                yield found


def _c_forbidden(ctx):
    record = ctx.report if ctx.kind == REPORT else json.loads(_package_json(ctx.subject) or "{}")
    return [_finding("boundary.forbidden_fields", {"kind": ctx.kind, "ref": None}, pointer,
                     "fields:none_forbidden", "extra", section=_section_of(pointer))
            for pointer in _forbidden_keys(record, "")]


def load_schema(name):
    with io.open(os.path.join(_SCHEMAS, name), encoding="utf-8") as handle:
        return json.load(handle)


def _schema_findings(check_id, instance, schema_name, component, location):
    try:
        errors = jsonschema_mini.validate(json.loads(json.dumps(instance, default=str)),
                                          load_schema(schema_name))
    except Exception:
        errors = ["unvalidated"]
    return [] if not errors else [_finding(check_id, component, location,
                                           "schema:%s" % schema_name, "invalid")]


def _c_schema_subject(ctx):
    if ctx.kind == REPORT:
        return _schema_findings("schema.subject", ctx.report, "executive_report.schema.json",
                                {"kind": "executive_report", "ref": ctx.report.get("report_id")},
                                None)
    record = _package_json(ctx.subject)
    if record is None:
        return [_finding("schema.subject", {"kind": "decision_package", "ref": None}, None,
                         "schema:decision_support.schema.json", "unbound")]
    return _schema_findings("schema.subject", json.loads(record), "decision_support.schema.json",
                            {"kind": "decision_package", "ref": None}, None)


def _c_schema_components(ctx):
    found = []
    strategy = _strategy_of(ctx)
    if strategy is not None:
        try:
            found += _schema_findings("schema.components", strategy.as_dict(),
                                      "strategy.schema.json",
                                      {"kind": "strategy_result", "ref": None}, None)
        except contract_mod.SynthesisError:
            found.append(_finding("schema.components", {"kind": "strategy_result", "ref": None},
                                  None, "schema:strategy.schema.json", "unbound"))
    if ctx.kind == REPORT:
        if ctx.subject._swot is not None:
            found += _schema_findings("schema.components", ctx.subject._swot, "swot.schema.json",
                                      {"kind": "swot", "ref": None}, None)
        for position, (package, digest) in enumerate(ctx.subject._packages):
            record = _package_json(package)
            if record is None:
                found.append(_finding("schema.components",
                                      {"kind": "decision_package", "ref": digest}, None,
                                      "schema:decision_support.schema.json", "unbound",
                                      position=position))
            else:
                found += _schema_findings("schema.components", json.loads(record),
                                          "decision_support.schema.json",
                                          {"kind": "decision_package", "ref": digest}, None)
    return found


_CHECKS = {
    "input.genuine_draft": _c_input, "binding.synthesis": _c_binding_synthesis,
    "binding.strategy": _c_binding_strategy, "binding.decision_packages": _c_binding_packages,
    "binding.swot": _c_binding_swot, "binding.sources_record": _c_binding_sources,
    "synthesis.genuine_strict": _c_genuine_strict, "synthesis.quality_grade": _c_quality,
    "synthesis.statement_ids": _c_statement_ids, "synthesis.registry_agreement": _c_registry,
    "reproduction.swot": _c_reproduction_swot, "reproduction.strategy": _c_reproduction_strategy,
    "reproduction.decision_package": _c_reproduction_package,
    "reproduction.report": _c_reproduction_report,
    "recomputation.request": _c_request, "recomputation.relay": _c_relay,
    "recomputation.record": _c_record, "recomputation.source": _c_source,
    "recomputation.configuration": _c_configuration, "recomputation.execution": _c_execution,
    "recomputation.coverage": _c_coverage, "recomputation.kpi": _c_kpi,
    "recomputation.statement": _c_statement,
    "section.set": _c_section_set, "section.order": _c_section_order,
    "section.status": _c_section_status, "section.availability": _c_availability,
    "content.statements": _c_statements, "content.summary": _c_summary,
    "content.kpi": _c_kpi_section, "content.anomalies": _c_anomalies,
    "content.strategy": _c_strategy_section, "content.swot": _c_swot_section,
    "content.decision_packages": _c_packages_section,
    "content.evidence_and_uncertainty": _c_evidence_section,
    "provenance.evidence_kinds": _c_evidence_kinds, "provenance.owned_content": _c_owned_content,
    "provenance.framing": _c_framing, "provenance.external_trust": _c_external_trust,
    "provenance.outlook": _c_outlook,
    "lifecycle.draft_input": _c_draft_input, "lifecycle.packages_final": _c_packages_final,
    "boundary.fixed_text": _c_fixed_text, "boundary.forbidden_fields": _c_forbidden,
    "schema.subject": _c_schema_subject, "schema.components": _c_schema_components,
}


# ---------------------------------------------------------------------------
# verify()
# ---------------------------------------------------------------------------

def verify(draft, relay=None):
    """Verify one genuine draft and return its `VerificationResult`.

    `relay` is the `recompute` operation's envelope text exactly as the verifier agent returned
    it, or `None` when `issue_recomputation()` returned `None`. It is untrusted: it only locates
    a record, which is then bound to the request re-derived from the draft here. A genuine draft
    that does not pass returns a `failed` result; anything else raises `VerificationError`.
    """
    kind = _subject_kind(draft)
    ctx = _Context(kind, draft, relay)
    checks, findings = [], []
    halted = False
    for check_id, category, method, applies_to, _message in CATALOGUE:
        if kind not in applies_to:
            checks.append({"check_id": check_id, "category": category, "method": method,
                           "outcome": "not_applicable"})
            continue
        if halted:
            outcome, produced = "not_run", []
        else:
            try:
                produced = _CHECKS[check_id](ctx)
                if produced is None:
                    outcome, produced = "not_applicable", []
                else:
                    outcome = "failed" if any(f["check_id"] == check_id for f in produced) \
                        else "passed"
            except _NotRun:
                outcome, produced = "not_run", []
        findings.extend(produced)
        checks.append({"check_id": check_id, "category": category, "method": method,
                       "outcome": outcome})
        if check_id == "input.genuine_draft" and outcome == "failed":
            halted = True
    # A relay finding raised inside the request check belongs to the relay check's outcome.
    outcomes = dict((c["check_id"], c) for c in checks)
    for finding in findings:
        entry = outcomes[finding["check_id"]]
        if entry["outcome"] in ("passed", "not_applicable"):
            entry["outcome"] = "failed"
    if any(f["check_id"].startswith("recomputation.") for f in findings):
        ctx.recomputation_status = FAILED
    elif ctx.plan is not None and ctx.plan.items and not halted:
        ctx.recomputation_status = "completed"

    ordered = []
    for finding in findings:
        catalogue = dict((entry[0], entry) for entry in CATALOGUE)[finding["check_id"]]
        section = finding.pop("_section")
        position = finding.pop("_position")
        public = {
            "check_id": finding["check_id"], "category": catalogue[1], "method": catalogue[2],
            "component": finding["component"], "location": finding["location"],
            "expected": finding["expected"], "observed": finding["observed"],
            "message": catalogue[4]}
        seed = runner_mod.canonical_json(public)
        public = dict([("finding_id", "vf-" + hashlib.sha256(seed.encode("utf-8"))
                        .hexdigest()[:12])] + list(public.items()))
        key = (_CATALOGUE_INDEX[public["check_id"]],
               report_mod.SECTION_ORDER.index(section) if section in report_mod.SECTION_ORDER
               else len(report_mod.SECTION_ORDER), position, public["location"] or "",
               public["finding_id"])
        ordered.append((key, public))
    ordered = [public for _key, public in sorted(ordered, key=lambda pair: pair[0])]

    subject = {"kind": SUBJECT_REPORT if kind == REPORT else SUBJECT_PACKAGE,
               "report_id": ctx.report.get("report_id") if kind == REPORT else None,
               "digest": _subject_digest(kind, draft)}
    components = _components(ctx)
    runs = []
    if ctx.record is not None:
        registered = dict((r["run_id"], r) for r in ctx.synthesis.registered_runs())
        for run in _record_runs(ctx):
            held = registered.get(run.get("run_id"), {})
            runs.append({"run_id": run.get("run_id"), "dataset_id": held.get("dataset_id"),
                         "command_id": held.get("command_id"),
                         "source_status": run.get("source_status"),
                         "config_status": run.get("config_status"),
                         "run_status": run.get("run_status")})
    status = PASSED if not ordered else FAILED
    identity = runner_mod.canonical_json({"subject": subject, "checks": checks,
                                          "findings": ordered})
    record = {
        "schema_version": SCHEMA_VERSION,
        "analysis": ANALYSIS,
        "verified_by": VERIFIED_BY,
        "verification_id": "ver-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12],
        "subject": subject,
        "status": status,
        "finalisation_permitted": status == PASSED,
        "synthesis_digest": strategy_mod.synthesis_digest(ctx.synthesis),
        "components": components,
        "recomputation": {
            "status": ctx.recomputation_status, "executor": EXECUTOR,
            "request_id": ctx.plan.request_id if ctx.plan is not None else None,
            "record_id": ctx.record_id, "runs": runs,
            "figures_checked": ctx.figures_checked},
        "checks": checks,
        "findings": ordered,
        "verification_note": VERIFICATION_NOTE,
        "human_decision": HUMAN_DECISION,
        "trust_statement": set_mod.TRUST_STATEMENT,
    }
    for path in ctx.consumed:
        _remove_quietly(path)
    return VerificationResult(draft, record, _token=_BUILD_TOKEN)


def _components(ctx):
    strategy = _strategy_of(ctx)
    components = {"strategy": None, "swot": None, "decision_packages": []}
    if strategy is not None:
        try:
            components["strategy"] = {"digest": _sha256_text(strategy.to_json())}
        except contract_mod.SynthesisError:
            components["strategy"] = {"digest": None}
    if ctx.kind == REPORT:
        if ctx.subject._swot is not None:
            components["swot"] = {"digest": ctx.subject._swot_digest}
        for package, digest in ctx.subject._packages:
            final = type(package) is FinalDecisionResult
            components["decision_packages"].append({
                "digest": digest, "lifecycle": FINAL if final else DRAFT,
                "verification_id": package.verification.verification_id if final else None})
    return components


# ---------------------------------------------------------------------------
# VerificationResult
# ---------------------------------------------------------------------------

class VerificationResult(object):
    """The deterministic record of one verification. Built only by `verify()`."""

    __slots__ = ("_draft", "_record")

    def __init__(self, draft, record, _token=None):
        if _token is not _BUILD_TOKEN:
            raise VerificationError(
                "a VerificationResult is produced only by verification.verify(); a caller-made "
                "result, status or finding is never accepted")
        self._draft = draft
        self._record = record

    @property
    def verification_id(self):
        return self._record["verification_id"]

    @property
    def status(self):
        return self._record["status"]

    @property
    def passed(self):
        return self._record["status"] == PASSED

    @property
    def findings(self):
        return copy.deepcopy(self._record["findings"])

    @property
    def subject_digest(self):
        return self._record["subject"]["digest"]

    def is_for(self, draft):
        return draft is self._draft

    def as_dict(self):
        return copy.deepcopy(self._record)

    def to_json(self, indent=None):
        """Deterministic serialisation in contract key order."""
        return json.dumps(self._record, indent=indent, default=str)

    def verification_record(self):
        """The record a final artifact carries beside its unedited content (ADR-0034 section 8)."""
        recomputation = self._record["recomputation"]
        return {"verification_id": self._record["verification_id"],
                "verified_by": VERIFIED_BY,
                "subject_digest": self._record["subject"]["digest"],
                "synthesis_digest": self._record["synthesis_digest"],
                "recomputation_status": recomputation["status"],
                "request_id": recomputation["request_id"],
                "record_id": recomputation["record_id"]}

    def __repr__(self):
        return "VerificationResult(%s, %s)" % (self.status, self.verification_id)


# ---------------------------------------------------------------------------
# Final artifacts and finalise()
# ---------------------------------------------------------------------------

def _still_valid(kind, draft, verification):
    """Whether a passed verification still describes this draft and its bindings exactly."""
    if not (type(verification) is VerificationResult and verification.is_for(draft)
            and verification.passed):
        return False
    if not draft.is_bound_to(draft.synthesis):
        return False
    if strategy_mod.synthesis_digest(draft.synthesis) \
            != verification._record["synthesis_digest"]:
        return False
    if _subject_digest(kind, draft) != verification.subject_digest:
        return False
    if kind == REPORT:
        for package, _digest in draft._packages:
            if type(package) is not FinalDecisionResult \
                    or not package.is_bound_to(draft.synthesis):
                return False
    return True


class FinalDecisionResult(object):
    """A final decision package: the unedited draft and its passed verification, side by side."""

    __slots__ = ("_draft", "_verification")

    def __init__(self, draft, verification, _token=None):
        if _token is not _BUILD_TOKEN:
            raise VerificationError("a final package is produced only by verification.finalise()")
        self._draft = draft
        self._verification = verification

    draft = property(lambda self: self._draft)
    verification = property(lambda self: self._verification)
    synthesis = property(lambda self: self._draft.synthesis)
    synthesis_digest = property(lambda self: self._draft.synthesis_digest)
    strategy_result = property(lambda self: self._draft.strategy_result)
    lifecycle = property(lambda self: FINAL)

    @property
    def body(self):
        return self._draft.body

    def is_bound_to(self, synthesis):
        return synthesis is self._draft.synthesis and _still_valid(PACKAGE, self._draft,
                                                                   self._verification)

    def as_dict(self):
        if not self.is_bound_to(self._draft.synthesis):
            raise VerificationError(
                "the draft or a binding changed after verification; this final package is stale "
                "and is refused, never downgraded")
        record = self._draft.as_dict()
        record["lifecycle"] = FINAL
        record["verification"] = VERIFIED
        record["lifecycle_note"] = FINAL_PACKAGE_NOTE
        record["verification_record"] = self._verification.verification_record()
        return record

    def to_json(self, indent=None):
        return json.dumps(self.as_dict(), indent=indent, default=str)

    def __repr__(self):
        return "FinalDecisionResult(%s)" % self._verification.verification_id


class FinalExecutiveReportResult(object):
    """A final executive report: the unedited draft and its passed verification, side by side."""

    __slots__ = ("_draft", "_verification")

    def __init__(self, draft, verification, _token=None):
        if _token is not _BUILD_TOKEN:
            raise VerificationError("a final report is produced only by verification.finalise()")
        self._draft = draft
        self._verification = verification

    draft = property(lambda self: self._draft)
    verification = property(lambda self: self._verification)
    synthesis = property(lambda self: self._draft.synthesis)
    lifecycle = property(lambda self: FINAL)

    @property
    def report_id(self):
        """Unchanged by finalisation: it is content-addressed over content, not lifecycle."""
        return self._draft.report_id

    @property
    def verification_id(self):
        return self._verification.verification_id

    def is_bound_to(self, synthesis):
        return synthesis is self._draft.synthesis and _still_valid(REPORT, self._draft,
                                                                   self._verification)

    def as_dict(self):
        if not self.is_bound_to(self._draft.synthesis):
            raise VerificationError(
                "the draft or a binding changed after verification; this final report is stale "
                "and is refused, never downgraded")
        record = self._draft.as_dict()
        for holder in (record, record["sections"][report_mod.REPORTING_FRAME]):
            holder["lifecycle"] = FINAL
            holder["verification"] = VERIFIED
            holder["lifecycle_note"] = FINAL_REPORT_NOTE
        record["verification_record"] = self._verification.verification_record()
        return record

    def to_json(self, indent=None):
        return json.dumps(self.as_dict(), indent=indent, default=str)

    def __repr__(self):
        return "FinalExecutiveReportResult(%s, %s)" % (self.report_id, self.verification_id)


def finalise(draft, verification):
    """Return the final artifact for a draft whose verification passed and still holds.

    Refuses - raising `VerificationError` and returning nothing - for a final or non-genuine
    subject, a verification that failed, belongs to another draft or is not a genuine result,
    or any binding or content that changed since verification. Nothing is repaired or rebuilt.
    """
    kind = _subject_kind(draft)
    if type(verification) is not VerificationResult:
        raise VerificationError(
            "finalisation takes the VerificationResult verification.verify() returned for this "
            "draft; a serialised or caller-made result is never accepted")
    if not verification.is_for(draft):
        raise VerificationError("this verification belongs to a different draft object")
    if not verification.passed:
        raise VerificationError(
            "verification failed with %d finding(s); every finding blocks finalisation, and the "
            "draft stays a draft" % len(verification._record["findings"]))
    if not _still_valid(kind, draft, verification):
        raise VerificationError(
            "the draft, the synthesis set or a component changed after verification; verify the "
            "draft again rather than finalising stale content")
    if kind == REPORT:
        return FinalExecutiveReportResult(draft, verification, _token=_BUILD_TOKEN)
    return FinalDecisionResult(draft, verification, _token=_BUILD_TOKEN)


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def render(result):
    """The verification result as markdown, formatted once. Adds no finding and no explanation."""
    record = result.as_dict() if isinstance(result, VerificationResult) else result
    subject = record["subject"]
    lines = ["# Verification — %s" % record["status"], "",
             "Verification `%s` · %s `%s` · subject digest `%s`" % (
                 record["verification_id"], subject["kind"].replace("_", " "),
                 subject["report_id"] or "-", subject["digest"]), "",
             "> %s" % record["human_decision"], "", "_%s_" % record["verification_note"], "",
             "**Finalisation permitted:** %s" % ("yes" if record["finalisation_permitted"]
                                                 else "no"), "",
             "**Recomputation:** %s (%d fields compared)" % (
                 record["recomputation"]["status"], record["recomputation"]["figures_checked"]),
             "", "| Check | Category | Method | Outcome |", "|---|---|---|---|"]
    lines += ["| `%s` | %s | %s | %s |" % (c["check_id"], c["category"], c["method"],
                                             c["outcome"]) for c in record["checks"]]
    lines += ["", "## Findings", ""]
    if not record["findings"]:
        lines.append("_None._")
    for finding in record["findings"]:
        lines.append("- `%s` %s — %s `%s`: expected `%s`, observed `%s`%s" % (
            finding["finding_id"], finding["check_id"], finding["component"]["kind"],
            finding["component"]["ref"] or "-", finding["expected"], finding["observed"],
            " at `%s`" % finding["location"] if finding["location"] else ""))
        lines.append("  - %s" % finding["message"])
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "issue_recomputation", "recompute_request", "verify", "finalise", "render", "envelope",
    "valid_arguments", "field_digest", "canonical", "verification_directory", "load_schema",
    "VerificationResult", "FinalDecisionResult", "FinalExecutiveReportResult",
    "VerificationError", "CATALOGUE", "CHECK_IDS", "CATEGORIES", "METHODS", "OUTCOMES",
    "OBSERVED_CODES", "ERROR_CODES", "KPI_FIELDS", "ANALYSIS_FIELDS", "REQUEST_ID", "RECORD_ID",
    "VERIFICATION_ID", "RESULT_PROTOCOL", "REQUEST_PROTOCOL", "RECORD_PROTOCOL", "VERIFIED_BY",
    "FINAL_REPORT_NOTE", "FINAL_PACKAGE_NOTE", "HUMAN_DECISION", "VERIFICATION_NOTE",
    "NULL_MARKER", "ENV_DIRECTORY",
]
