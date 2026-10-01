# -*- coding: utf-8 -*-
"""Decision Support: a twelve-part draft decision package beside the synthesis set (ADR-0032).

A decision package structures **one user-supplied decision question** around options, criteria,
evidence, tradeoffs, risks and expected outcomes, over one genuine strict `SynthesisSet`. It is
the second class-7 consumer, and it deliberately owns almost nothing: evidence is resolved by
`synthesis.grounding` through `strategy.cite()`, recommendation records are built by
`strategy.ground_recommendation()` with `issued_by: "bops-decision-support"`, figures are held to
the evidence by `strategy.require_grounded()`, and every confidence is
`synthesis.confidence.combine()` over reason codes the set already derived. What this module adds
is the package structure and the rules ADR-0032 attaches to it.

**What the caller supplies is framing, never evidence.** The decision question, objective,
constraints, option labels, criteria, not-assessable labels, divergence notes and next steps are
stored verbatim with their origin. None of them becomes a synthesis statement, none grounds
anything except that a referenced criterion may be quoted, and none leaves the machine.

**What the caller cannot supply.** Confidence, support, trust, verification, lifecycle, scores,
weights, ranks, priorities, severities, likelihoods: every request and part record is a closed
set of fields, so there is nowhere to put one.

**Preferred option.** Stated only when ADR-0032 §10's four conditions all hold; otherwise it is
`null` and a fixed, deterministic reason says which condition failed. It is never a ranking: at
most one option is preferred and the others keep presentation order.

**Lifecycle.** Every package this module builds is a `draft`. There is no path here to `final`;
finalising is the M11 verifier's operation, recorded beside a draft without editing it.

**What this module never does.** It reads no file, runs no analysis, retrieves nothing, dispatches
nothing, writes nothing to the synthesis set, executes no decision and transmits nothing.
"""

import copy
import hashlib
import json

from . import config as config_mod
from . import strategy as strategy_mod
from .synthesis import confidence as confidence_mod
from .synthesis import contract as contract_mod
from .synthesis import grounding
from .synthesis import limitations as limitations_mod
from .synthesis import synthesis_set as set_mod

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "decision_support"
ISSUED_BY = strategy_mod.DECISION_SUPPORT_ISSUER

DRAFT = "draft"
FINAL = "final"
LIFECYCLES = (DRAFT, FINAL)

#: Stated so a test can assert it: this milestone produces drafts only.
PRODUCES_FINAL = False
EXECUTES_ACTIONS = False

UNVERIFIED = "unverified"
LIFECYCLE_NOTE = (
    "Draft decision package. It has not been checked by the analysis verifier, which alone can "
    "move a draft to final, and it must be presented as unverified wherever it appears.")

HUMAN_DECISION = (
    "This is draft decision analysis for a person to decide on. BusinessOps does not make or "
    "execute the decision: acting on it - a system write, a message, an export or an overwrite "
    "- needs that person's decision and explicit per-action approval, and financial "
    "transactions are prohibited.")

ORDER_NOTE = (
    "Options appear in presentation order - the user's options, then options from "
    "recommendation records, then the status quo - and tradeoffs, risks and outcomes follow "
    "their option and the position of their earliest cited statement in the synthesis set. No "
    "order here is a ranking, a priority or a preference.")

STATUS_QUO_LABEL = "Make no change"

USER = "user"
RECOMMENDATION = "recommendation"
STATUS_QUO = "status_quo"
CONFIGURATION = "configuration"

#: The twelve parts, in the order ADR-0032 fixes.
PART_ORDER = ("decision_question", "business_context", "objective", "options", "criteria",
              "evidence", "assumptions", "tradeoffs", "risks", "expected_outcomes", "guidance",
              "uncertainty")

#: The request a skill or command passes. Closed: any other field is refused.
REQUEST_FIELDS = ("decision_question", "objective", "constraints", "options",
                  "include_status_quo", "criteria", "materiality_criteria", "recommendations",
                  "tradeoffs", "risks", "expected_outcomes", "not_assessable",
                  "preferred_option", "preference_criteria", "divergences", "next_steps")

TRADEOFF_FIELDS = ("options", "criteria", "text", "evidence", "assumptions")
RISK_FIELDS = ("option", "text", "evidence")
OUTCOME_FIELDS = ("option", "text", "evidence")
NOT_ASSESSABLE_FIELDS = ("option", "reason")
DIVERGENCE_FIELDS = ("recommendations", "note")
NEXT_STEP_FIELDS = ("text", "addresses")
ADDRESS_FIELDS = ("kind", "ref")
ADDRESS_KINDS = ("limitation", "conflict", "unresolved_dimension")

#: The materiality thresholds a user may ask to use as criteria (the configured policy's keys).
MATERIALITY_KEYS = ("absolute_amount", "percentage", "kpi_deviation", "revenue_percentage",
                    "margin_percentage_points")

#: The limitation code recording that the user labelled an option not assessable.
NOT_ASSESSABLE = "decision_support.option_not_assessable"

#: Why no option is preferred. Fixed text, chosen by which ADR-0032 §10 condition failed.
NO_PREFERENCE_REQUESTED = "No preferred option was requested."
NO_PREFERENCE_CRITERIA = ("No decision criteria were stated, so no option can be preferred "
                          "against them.")
NO_PREFERENCE_BASIS = ("A preferred option was requested without naming the criteria it is "
                       "preferred against.")
NO_PREFERENCE_RECORD = ("The requested option has no recommendation record, so there is no "
                        "grounded basis for preferring it.")
NO_PREFERENCE_UNRELATED = ("No tradeoff relates the requested option's recommendation evidence "
                           "to the named criteria.")
NO_PREFERENCE_UNASSESSED = ("At least one other option is neither assessed against the criteria "
                            "the preference rests on nor labelled not assessable.")

_BUILD_TOKEN = object()


class DecisionSupportError(contract_mod.SynthesisError):
    """A decision package or its input violates ADR-0032. Raised, never degraded."""


def _checked(call, *args, **kwargs):
    """Run a shared rule, reporting its refusal as this capability's error."""
    try:
        return call(*args, **kwargs)
    except (grounding.GroundingError, strategy_mod.StrategyError) as refusal:
        raise DecisionSupportError(str(refusal))


def _content_id(prefix, *parts):
    seed = "|".join(str(p) for p in parts)
    return prefix + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _closed(record, fields, what, required=()):
    if not isinstance(record, dict):
        raise DecisionSupportError("%s is a record of %s" % (what, ", ".join(fields)))
    extra = sorted(set(record) - set(fields))
    if extra:
        raise DecisionSupportError(
            "%s carries only %s; %s is not accepted. Confidence, trust, lifecycle and every "
            "other conclusion are derived, and nothing is scored, weighted, ranked or "
            "prioritised." % (what, ", ".join(fields), ", ".join(str(e) for e in extra)))
    missing = [name for name in required if name not in record]
    if missing:
        raise DecisionSupportError("%s must state %s" % (what, ", ".join(missing)))
    return record


def _records(request, name):
    """A list-valued request field, or a refusal. Absent means empty."""
    values = request.get(name)
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise DecisionSupportError("%s is a list of records" % name)
    return list(values)


def _texts(values, what):
    if values is None:
        return []
    if not isinstance(values, (list, tuple)) or not all(_text(v) for v in values):
        raise DecisionSupportError("%s is a list of non-empty text" % what)
    if len(set(values)) != len(values):
        raise DecisionSupportError("%s names the same text twice" % what)
    return list(values)


def _assessment(record):
    return confidence_mod.assess(record.get("confidence_reasons") or [])


def _item_assessment(item):
    return confidence_mod.assess((item.confidence_detail or {}).get("reasons") or [])


# ---------------------------------------------------------------------------
# The question
# ---------------------------------------------------------------------------

def _question(value):
    """The decision question, or a refusal. Required, never inferred, never rewritten.

    The check is structural only: a question that is absent, not text, or blank is refused.
    Anything else is kept exactly as the user wrote it, several sentences and question marks
    included. Whether a question is ambiguous is a judgement about meaning that code cannot make
    reliably, so it belongs to the skill and command, which ask the user (ADR-0032 section 1).
    """
    if not isinstance(value, str) or not value.strip():
        raise DecisionSupportError(
            "a decision package needs a decision question from the user, as non-blank text; "
            "none was given, and one is never inferred from data or context")
    return {"text": value, "origin": USER}


# ---------------------------------------------------------------------------
# The result
# ---------------------------------------------------------------------------

class DecisionResult:
    """A draft twelve-part decision package grounded in one genuine strict synthesis set.

    Built only by `build()`. Holds the set object, the optional `StrategyResult` it packaged, and
    a digest of the set's exact state; `as_dict()` and `claims()` refuse once the set has changed
    or the strategy result no longer binds to it.
    """

    __slots__ = ("_synthesis", "_strategy_result", "_digest", "_body", "_issued", "_request",
                 "_config")

    def __init__(self, synthesis, strategy_result, digest, body, issued, request=None,
                 config=None, _token=None):
        if _token is not _BUILD_TOKEN:
            raise DecisionSupportError(
                "a DecisionResult is built by decision_support.build() from a genuine synthesis "
                "set; a package assembled elsewhere was never grounded in one")
        self._synthesis = synthesis
        self._strategy_result = strategy_result
        self._digest = digest
        self._body = body
        self._issued = issued
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
    def strategy_result(self):
        """The `StrategyResult` this package was built with, or `None`. Read-only.

        Exposed so an assembler can require the same object rather than a second set of records
        (ADR-0033 section 1); the result itself is immutable to its holder.
        """
        return self._strategy_result

    @property
    def request(self):
        """A copy of the request this package was built from. Read-only (ADR-0034 section 5.2)."""
        return copy.deepcopy(self._request)

    @property
    def config(self):
        """The `ResolvedConfig` this package was built with, or `None`. Read-only."""
        return self._config

    @property
    def body(self):
        """A copy of the twelve parts, in order."""
        return copy.deepcopy(self._body)

    def is_bound_to(self, synthesis):
        return (synthesis is self._synthesis
                and strategy_mod.synthesis_digest(synthesis) == self._digest
                and (self._strategy_result is None
                     or self._strategy_result.is_bound_to(synthesis)))

    def _require_bound(self):
        if not self.is_bound_to(self._synthesis):
            raise DecisionSupportError(
                "the synthesis set changed after this decision package was grounded; build it "
                "again rather than carrying its conclusions onto different evidence")

    def claims(self):
        """Class-7 claims for the records Decision Support issued. Strategy's stay Strategy's."""
        self._require_bound()
        return [_checked(strategy_mod._claim, record) for record in self._issued]

    def record_in(self, ledger):
        return [ledger.add(claim) for claim in self.claims()]

    def as_dict(self):
        self._require_bound()
        synthesis = self._synthesis
        cited = set(entry["synthesis_id"] for entry in self._body["evidence"])
        return {
            "schema_version": SCHEMA_VERSION,
            "analysis": ANALYSIS,
            "issued_by": ISSUED_BY,
            "lifecycle": DRAFT,
            "verification": UNVERIFIED,
            "lifecycle_note": LIFECYCLE_NOTE,
            "subject": synthesis.subject,
            "as_of": synthesis.as_of,
            "business_model": synthesis.business_model,
            "currency": synthesis.currency,
            "quality_grade": synthesis.quality_grade,
            "synthesis_digest": self._digest,
            "strategy_result_bound": self._strategy_result is not None,
            "trust_statement": set_mod.TRUST_STATEMENT,
            "human_decision": HUMAN_DECISION,
            "order_note": ORDER_NOTE,
            "body": copy.deepcopy(self._body),
            "material_not_cited": [item.id for item in synthesis.material()
                                   if item.id not in cited],
            "conflicts": [conflict.as_dict() for conflict in synthesis.conflicts],
            "limitations": limitations_mod.as_dicts(synthesis.limitations),
            "confidence": synthesis.confidence().as_dict(),
        }

    def to_json(self, indent=None):
        """Deterministic serialisation. Key order is the contract's, so keys are not sorted."""
        return json.dumps(self.as_dict(), indent=indent, default=str)

    def __repr__(self):
        return "DecisionResult(draft, %d options)" % len(self._body["options"])


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(synthesis, request, strategy_result=None, config=None):
    """Build a draft decision package, or raise `DecisionSupportError` and emit nothing.

    `request` is a closed record of `REQUEST_FIELDS`; only `decision_question` is required.
    `strategy_result`, if given, must be the `StrategyResult` built over this very set object.
    `config` is a `ResolvedConfig`, needed only when `materiality_criteria` names thresholds.
    """
    synthesis = _checked(grounding.genuine_set, synthesis)
    if strategy_result is not None:
        if type(strategy_result) is not strategy_mod.StrategyResult:
            raise DecisionSupportError(
                "a strategy input is the StrategyResult strategy.build() produced; a serialised "
                "result or a look-alike was never grounded")
        if not strategy_result.is_bound_to(synthesis):
            raise DecisionSupportError(
                "the StrategyResult is not bound to this synthesis set - a different set, or "
                "the same set changed since - so its records cannot be packaged with it")
    request = _closed(request, REQUEST_FIELDS, "a decision request",
                      required=("decision_question",))

    index = grounding.index(synthesis)
    digest = strategy_mod.synthesis_digest(synthesis)

    question = _question(request["decision_question"])
    objective_text = request.get("objective")
    if objective_text is not None and not _text(objective_text):
        raise DecisionSupportError("an objective, where given, is non-empty text")
    objective = {"text": objective_text, "origin": USER if objective_text else None,
                 "stated": objective_text is not None}
    context = {"subject": synthesis.subject, "business_model": synthesis.business_model,
               "currency": synthesis.currency,
               "constraints": [{"text": text, "origin": USER}
                               for text in _texts(request.get("constraints"), "constraints")]}

    # -- guidance records ---------------------------------------------------
    records, first_positions, issued = [], {}, []
    if strategy_result is not None:
        records.extend(strategy_result.recommendations)
    for raw in _records(request, "recommendations"):
        position, record = _checked(strategy_mod.ground_recommendation, synthesis, index, raw,
                                    issued_by=ISSUED_BY)
        records.append(record)
        issued.append(record)
        first_positions[record["recommendation_id"]] = position
    ids = [record["recommendation_id"] for record in records]
    if len(set(ids)) != len(ids):
        raise DecisionSupportError(
            "a recommendation appears twice in guidance - the same action on the same evidence "
            "is one record; package the existing one rather than issuing a copy")
    records_by_id = dict((record["recommendation_id"], record) for record in records)

    # -- options --------------------------------------------------------------
    include_status_quo = request.get("include_status_quo", True)
    if not isinstance(include_status_quo, bool):
        raise DecisionSupportError("include_status_quo is true or false")
    options = []
    for label in _texts(request.get("options"), "options"):
        options.append({"option_id": _content_id("opt-", USER, label), "label": label,
                        "origin": USER, "recommendation_id": None})
    for record in records:
        options.append({"option_id": _content_id("opt-", RECOMMENDATION,
                                                 record["recommendation_id"]),
                        "label": record["action"], "origin": RECOMMENDATION,
                        "recommendation_id": record["recommendation_id"]})
    if include_status_quo:
        options.append({"option_id": _content_id("opt-", STATUS_QUO, STATUS_QUO_LABEL),
                        "label": STATUS_QUO_LABEL, "origin": STATUS_QUO,
                        "recommendation_id": None})
    labels = [option["label"] for option in options]
    if len(set(labels)) != len(labels):
        raise DecisionSupportError(
            "two options share a label; each option must be distinguishable, so rename one")
    if len(options) < 2:
        raise DecisionSupportError(
            "a decision needs at least two options and this request forms %d; ask the user "
            "what the alternatives are" % len(options))
    option_by_label = dict((option["label"], option) for option in options)
    option_order = dict((option["option_id"], i) for i, option in enumerate(options))

    def option_for(label, what):
        if not isinstance(label, str) or label not in option_by_label:
            raise DecisionSupportError("%s names option %r, which is not an option in this "
                                       "package" % (what, label))
        return option_by_label[label]

    # -- criteria -------------------------------------------------------------
    criteria = []
    for text in _texts(request.get("criteria"), "criteria"):
        criteria.append({"criterion_id": _content_id("crit-", USER, text), "text": text,
                         "origin": USER, "source": None})
    materiality = request.get("materiality_criteria") or []
    if materiality:
        if type(config) is not config_mod.ResolvedConfig:
            raise DecisionSupportError(
                "a materiality criterion is read from the resolved configuration, and none was "
                "given; a threshold is never typed in by the caller")
        for key in _texts(materiality, "materiality_criteria"):
            if key not in MATERIALITY_KEYS:
                raise DecisionSupportError("%r is not a configured materiality threshold; the "
                                           "thresholds are %s" % (key, ", ".join(MATERIALITY_KEYS)))
            dotted = "materiality.%s" % key
            value = config.get(dotted)
            layer = config.source_of(dotted)
            if value is None or layer is None:
                raise DecisionSupportError("the configuration holds no %s" % dotted)
            text = "Materiality threshold %s: %s" % (key, value)
            criteria.append({"criterion_id": _content_id("crit-", CONFIGURATION, dotted),
                             "text": text, "origin": CONFIGURATION,
                             "source": "%s (%s layer)" % (dotted, layer)})
    criterion_by_text = dict((c["text"], c) for c in criteria)
    if len(criterion_by_text) != len(criteria):
        raise DecisionSupportError("two criteria share the same text")

    def criteria_for(texts, what):
        found = []
        for text in _texts(texts, what):
            if text not in criterion_by_text:
                raise DecisionSupportError("%s names criterion %r, which is not a criterion in "
                                           "this package" % (what, text))
            found.append(criterion_by_text[text])
        return found

    # -- citations --------------------------------------------------------------
    def citations(values, what, required):
        if values is None:
            values = []
        if not isinstance(values, (list, tuple)):
            raise DecisionSupportError("%s evidence is a list of synthesis statement ids" % what)
        if required and not values:
            raise DecisionSupportError(
                "%s needs at least one evidence id; a claim about an option rests on evidence "
                "or is left out" % what)
        if not all(isinstance(v, str) for v in values):
            raise DecisionSupportError("%s evidence ids are strings" % what)
        if len(set(values)) != len(values):
            raise DecisionSupportError("%s cites the same statement twice" % what)
        return [_checked(strategy_mod.cite, index, value) for value in values]

    def assumptions_for(values, what):
        found = []
        for value in _texts(values, "%s assumptions" % what):
            _position, item = _checked(grounding.one, index, value)
            if not grounding.graded(item) or item.kind != contract_mod.ASSUMPTION:
                raise DecisionSupportError(
                    "%s names %s as an assumption, but it is a %s, not an assumption the set "
                    "registered" % (what, value, getattr(item, "kind", type(item).__name__)))
            found.append(item)
        return found

    def derived(items):
        assessment = confidence_mod.combine([_item_assessment(item) for item in items])
        return assessment.level, list(assessment.reasons)

    def earliest(cited):
        return min([position for position, _item, _domains in cited] or [len(synthesis.items)])

    # -- tradeoffs ----------------------------------------------------------------
    tradeoffs = []
    for raw in _records(request, "tradeoffs"):
        raw = _closed(raw, TRADEOFF_FIELDS, "a tradeoff", required=("options", "text",
                                                                     "evidence"))
        if not _text(raw["text"]):
            raise DecisionSupportError("a tradeoff's text must be non-empty")
        opts = [option_for(label, "a tradeoff")
                for label in _texts(raw["options"], "a tradeoff's options")]
        if not opts:
            raise DecisionSupportError("a tradeoff names at least one option")
        crits = criteria_for(raw.get("criteria"), "a tradeoff")
        cited = citations(raw["evidence"], "a tradeoff", required=True)
        assumed = assumptions_for(raw.get("assumptions"), "a tradeoff")
        cited_items = [item for _p, item, _d in cited]
        _checked(strategy_mod.require_grounded, "tradeoff", raw["text"],
                 [item.statement for item in cited_items] + [c["text"] for c in crits],
                 [item.id for item in cited_items])
        level, reasons = derived(cited_items + assumed)
        option_ids = sorted((o["option_id"] for o in opts), key=option_order.get)
        evidence_ids = [item.id for _p, item, _d in sorted(cited, key=lambda c: c[0])]
        record = {"tradeoff_id": _content_id("trd-", ",".join(option_ids), raw["text"],
                                             ",".join(evidence_ids)),
                  "option_ids": option_ids,
                  "criterion_ids": [c["criterion_id"] for c in crits],
                  "text": raw["text"], "evidence": evidence_ids,
                  "assumption_ids": [item.id for item in assumed],
                  "confidence": level, "confidence_reasons": reasons}
        tradeoffs.append(((option_order[option_ids[0]], earliest(cited),
                           record["tradeoff_id"]), record, cited, assumed))

    # -- risks ------------------------------------------------------------------
    risks = []
    for raw in _records(request, "risks"):
        raw = _closed(raw, RISK_FIELDS, "a risk", required=("option", "text"))
        if not _text(raw["text"]):
            raise DecisionSupportError("a risk's text must be non-empty")
        option = option_for(raw["option"], "a risk")
        cited = citations(raw.get("evidence"), "a risk", required=False)
        cited_items = [item for _p, item, _d in cited]
        _checked(strategy_mod.require_grounded, "risk", raw["text"],
                 [item.statement for item in cited_items], [item.id for item in cited_items])
        level, reasons = derived(cited_items)
        evidence_ids = [item.id for _p, item, _d in sorted(cited, key=lambda c: c[0])]
        record = {"risk_id": _content_id("rsk-", option["option_id"], raw["text"],
                                         ",".join(evidence_ids)),
                  "option_id": option["option_id"], "text": raw["text"],
                  "evidence": evidence_ids, "confidence": level,
                  "confidence_reasons": reasons}
        risks.append(((option_order[option["option_id"]], earliest(cited),
                       record["risk_id"]), record, cited))

    # -- expected outcomes ----------------------------------------------------------
    outcomes = []
    for raw in _records(request, "expected_outcomes"):
        raw = _closed(raw, OUTCOME_FIELDS, "an expected outcome",
                      required=("option", "text", "evidence"))
        if not _text(raw["text"]):
            raise DecisionSupportError("an expected outcome's text must be non-empty")
        option = option_for(raw["option"], "an expected outcome")
        cited = citations(raw["evidence"], "an expected outcome", required=True)
        cited_items = [item for _p, item, _d in cited]
        _checked(strategy_mod.require_grounded, "expected outcome", raw["text"],
                 [item.statement for item in cited_items], [item.id for item in cited_items])
        level, reasons = derived(cited_items)
        evidence_ids = [item.id for _p, item, _d in sorted(cited, key=lambda c: c[0])]
        record = {"outcome_id": _content_id("out-", option["option_id"], raw["text"],
                                            ",".join(evidence_ids)),
                  "option_id": option["option_id"], "text": raw["text"],
                  "evidence": evidence_ids, "confidence": level,
                  "confidence_reasons": reasons}
        outcomes.append(((option_order[option["option_id"]], earliest(cited),
                          record["outcome_id"]), record, cited))

    for kind, entries, id_key in (("tradeoff", tradeoffs, "tradeoff_id"),
                                  ("risk", risks, "risk_id"),
                                  ("expected outcome", outcomes, "outcome_id")):
        seen = [entry[1][id_key] for entry in entries]
        if len(set(seen)) != len(seen):
            raise DecisionSupportError("the same %s is given twice" % kind)
    tradeoffs.sort(key=lambda entry: entry[0])
    risks.sort(key=lambda entry: entry[0])
    outcomes.sort(key=lambda entry: entry[0])

    # -- not assessable ---------------------------------------------------------------
    not_assessable = {}
    for raw in _records(request, "not_assessable"):
        raw = _closed(raw, NOT_ASSESSABLE_FIELDS, "a not-assessable label",
                      required=("option", "reason"))
        option = option_for(raw["option"], "a not-assessable label")
        if not _text(raw["reason"]):
            raise DecisionSupportError("a not-assessable label gives its reason")
        _checked(strategy_mod.require_grounded, "not-assessable reason", raw["reason"], [], [])
        oid = option["option_id"]
        if oid in not_assessable:
            raise DecisionSupportError("option %r is labelled not assessable twice"
                                       % option["label"])
        if any(oid in t[1]["option_ids"] for t in tradeoffs) or any(
                o[1]["option_id"] == oid for o in outcomes):
            raise DecisionSupportError(
                "option %r is labelled not assessable but has tradeoffs or outcomes; it is one "
                "or the other" % option["label"])
        not_assessable[oid] = limitations_mod.Limitation(NOT_ASSESSABLE, option["label"],
                                                        raw["reason"])

    # -- evidence index -------------------------------------------------------------------
    cited_ids = set()
    for record in records:
        cited_ids.update(record["evidence"])
    for _key, record, _cited, *_rest in tradeoffs + risks + outcomes:
        cited_ids.update(record["evidence"])
    if not cited_ids:
        raise DecisionSupportError(
            "this package cites no evidence at all; a decision with nothing under it is not "
            "presented as analysis")
    evidence = []
    cited_items = []
    for position, item in enumerate(synthesis.items):
        if item.id in cited_ids:
            _checked(strategy_mod.cite, index, item.id)
            evidence.append(strategy_mod.statement_detail(synthesis, index, position, item))
            cited_items.append(item)

    # -- assumptions -------------------------------------------------------------------------
    referenced = {}
    for record in records:
        for dependency in record["dependencies"]:
            if dependency["assumption_id"]:
                referenced.setdefault(dependency["assumption_id"], []).append(
                    record["recommendation_id"])
    for _key, record, _cited, _assumed in tradeoffs:
        for assumption_id in record["assumption_ids"]:
            referenced.setdefault(assumption_id, []).append(record["tradeoff_id"])
    assumptions, assumed_items = [], []
    for position, item in enumerate(synthesis.items):
        if item.id in referenced:
            assumed_items.append(item)
            assumptions.append({"synthesis_id": item.id, "statement": item.statement,
                                "support": item.support, "confidence": item.confidence,
                                "confidence_reasons": list(
                                    (item.confidence_detail or {}).get("reasons") or []),
                                "referenced_by": list(referenced[item.id])})

    # -- per-option and package confidence ---------------------------------------------------
    per_option = []
    option_assessments = []
    for option in options:
        oid = option["option_id"]
        assessments = [_assessment(t[1]) for t in tradeoffs if oid in t[1]["option_ids"]]
        assessments += [_assessment(r[1]) for r in risks if r[1]["option_id"] == oid]
        assessments += [_assessment(o[1]) for o in outcomes if o[1]["option_id"] == oid]
        if option["recommendation_id"]:
            assessments.append(_assessment(records_by_id[option["recommendation_id"]]))
        combined = confidence_mod.combine(assessments)
        option_assessments.append(combined)
        per_option.append({"option_id": oid, "confidence": combined.level,
                           "confidence_reasons": list(combined.reasons)})
    package = confidence_mod.combine(option_assessments
                                     + [_assessment(record) for record in records])

    # -- conflicts, limitations, unresolved dimensions --------------------------------------
    conflicts_by_id = dict((conflict.id, conflict) for conflict in synthesis.conflicts)
    conflict_ids = []
    for item in cited_items + assumed_items:
        for conflict_id in sorted(item.conflict_refs):
            if conflict_id not in conflict_ids and conflict_id in conflicts_by_id:
                conflict_ids.append(conflict_id)
    conflicts = [conflicts_by_id[c].as_dict() for c in conflict_ids]
    # Limitations only accumulate: the cited statements' own, then the set's, then the options
    # the user labelled not assessable.
    limitations = limitations_mod.as_dicts(limitations_mod.merge(
        *([item.limitations for item in cited_items + assumed_items]
          + [synthesis.limitations]
          + [[not_assessable[o["option_id"]]] for o in options
             if o["option_id"] in not_assessable])))
    unresolved = []
    for detail in evidence:
        for dimension, reason in sorted(detail["unresolved_dimensions"].items()):
            unresolved.append({"synthesis_id": detail["synthesis_id"], "dimension": dimension,
                               "reason": reason})

    # -- next steps -----------------------------------------------------------------------------
    addressable = {
        "limitation": set(limitation["code"] for limitation in limitations),
        "conflict": set(conflict["conflict_id"] for conflict in conflicts),
        "unresolved_dimension": set("%s:%s" % (u["synthesis_id"], u["dimension"])
                                    for u in unresolved),
    }
    by_id = dict((item.id, item) for item in cited_items)
    next_steps = []
    for raw in _records(request, "next_steps"):
        raw = _closed(raw, NEXT_STEP_FIELDS, "a next step", required=("text", "addresses"))
        if not _text(raw["text"]):
            raise DecisionSupportError("a next step's text must be non-empty")
        address = _closed(raw["addresses"], ADDRESS_FIELDS, "a next step's addresses",
                          required=("kind", "ref"))
        if address["kind"] not in ADDRESS_KINDS:
            raise DecisionSupportError("a next step addresses a %s; the kinds are %s"
                                       % (address["kind"], ", ".join(ADDRESS_KINDS)))
        if address["ref"] not in addressable[address["kind"]]:
            raise DecisionSupportError(
                "a next step addresses %s %r, which this package does not carry; a next step is "
                "an evidence gap the package states, never a free-standing action"
                % (address["kind"], address["ref"]))
        # A next step cites nothing of its own, so a figure in it must be printed by the
        # statements behind what it addresses; a limitation has none (ADR-0032 section 6).
        if address["kind"] == "conflict":
            behind = [by_id[i] for i in conflicts_by_id[address["ref"]].item_ids if i in by_id]
        elif address["kind"] == "unresolved_dimension":
            behind = [by_id[address["ref"].split(":", 1)[0]]]
        else:
            behind = []
        _checked(strategy_mod.require_grounded, "next step", raw["text"],
                 [item.statement for item in behind], [item.id for item in behind])
        next_steps.append({"text": raw["text"],
                           "addresses": {"kind": address["kind"], "ref": address["ref"]}})

    # -- guidance -------------------------------------------------------------------------------
    divergences = []
    for raw in _records(request, "divergences"):
        raw = _closed(raw, DIVERGENCE_FIELDS, "a divergence",
                      required=("recommendations", "note"))
        rec_ids = _texts(raw["recommendations"], "a divergence's recommendations")
        if len(rec_ids) < 2 or any(r not in records_by_id for r in rec_ids):
            raise DecisionSupportError(
                "a divergence names at least two recommendation records present in guidance")
        if not _text(raw["note"]):
            raise DecisionSupportError("a divergence carries a note")
        texts = []
        for rec_id in rec_ids:
            texts.append(records_by_id[rec_id]["action"])
            texts.extend(detail["statement"]
                         for detail in records_by_id[rec_id]["evidence_detail"])
        _checked(strategy_mod.require_grounded, "divergence note", raw["note"], texts,
                 rec_ids)
        divergences.append({"recommendation_ids": rec_ids, "note": raw["note"]})

    preferred, basis, reason = _preference(request, options, option_by_label, criteria,
                                           criterion_by_text, records_by_id, tradeoffs,
                                           not_assessable)

    body = {
        "decision_question": question,
        "business_context": context,
        "objective": objective,
        "options": options,
        "criteria": criteria,
        "evidence": evidence,
        "assumptions": assumptions,
        "tradeoffs": [entry[1] for entry in tradeoffs],
        "risks": [entry[1] for entry in risks],
        "expected_outcomes": [entry[1] for entry in outcomes],
        "guidance": {"recommendations": copy.deepcopy(records),
                     "preferred_option": preferred, "preference_basis": basis,
                     "no_preference_reason": reason, "divergences": divergences},
        "uncertainty": {"confidence": package.level,
                        "confidence_reasons": list(package.reasons),
                        "options": per_option, "conflicts": conflicts,
                        "limitations": limitations, "unresolved_dimensions": unresolved,
                        "next_steps": next_steps},
    }

    if strategy_mod.synthesis_digest(synthesis) != digest:
        raise DecisionSupportError("the synthesis set changed while the package was built")
    return DecisionResult(synthesis, strategy_result, digest, body, issued, request=request,
                          config=config, _token=_BUILD_TOKEN)


def _preference(request, options, option_by_label, criteria, criterion_by_text, records_by_id,
                tradeoffs, not_assessable):
    """`(preferred_option_id, preference_basis, no_preference_reason)` under ADR-0032 section 10.

    All four conditions must hold, each checked over the named basis as a whole - there is no
    requirement of one tradeoff per criterion, and no criterion is scored or weighted:

    1. the package states at least one criterion;
    2. the option comes from a class-7 record in guidance, and at least one tradeoff about the
       option names a basis criterion and cites a statement that record cites - so the record's
       evidence is related to the criteria. The criteria those tradeoffs name are the ones the
       preference rests on;
    3. every other option is labelled not assessable, or appears in at least one tradeoff naming
       a criterion the preference rests on - so each is assessed against the same criteria;
    4. `preference_criteria` names the basis explicitly.

    Only tradeoffs can satisfy 2 and 3: ADR-0032 section 2 gives tradeoffs `criterion_ids` and
    gives expected outcomes none, so an outcome cannot say which criterion it is against.
    """
    label = request.get("preferred_option")
    named = request.get("preference_criteria")
    if label is None:
        if named:
            raise DecisionSupportError("preference_criteria were given without a preferred "
                                       "option")
        return None, None, NO_PREFERENCE_REQUESTED
    if not isinstance(label, str) or label not in option_by_label:
        raise DecisionSupportError("the preferred option %r is not an option in this package"
                                   % (label,))
    option = option_by_label[label]
    if not criteria:
        return None, None, NO_PREFERENCE_CRITERIA
    basis_texts = _texts(named, "preference_criteria")
    if not basis_texts:
        return None, None, NO_PREFERENCE_BASIS
    for text in basis_texts:
        if text not in criterion_by_text:
            raise DecisionSupportError("preference criterion %r is not a criterion in this "
                                       "package" % text)
    basis = [criterion_by_text[text]["criterion_id"] for text in basis_texts]
    record = records_by_id.get(option["recommendation_id"]) if option["recommendation_id"] \
        else None
    if record is None:
        return None, None, NO_PREFERENCE_RECORD

    record_evidence = set(record["evidence"])
    rests_on = set()
    for _key, tradeoff, _cited, _assumed in tradeoffs:
        if (option["option_id"] in tradeoff["option_ids"]
                and record_evidence & set(tradeoff["evidence"])):
            rests_on.update(set(tradeoff["criterion_ids"]) & set(basis))
    if not rests_on:
        return None, None, NO_PREFERENCE_UNRELATED

    for other in options:
        if other["option_id"] == option["option_id"]:
            continue
        if other["option_id"] in not_assessable:
            continue
        if not any(other["option_id"] in tradeoff["option_ids"]
                   and rests_on & set(tradeoff["criterion_ids"])
                   for _key, tradeoff, _cited, _assumed in tradeoffs):
            return None, None, NO_PREFERENCE_UNASSESSED

    return (option["option_id"],
            {"recommendation_id": record["recommendation_id"], "criterion_ids": basis},
            None)


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

_PART_TITLES = ("Decision question", "Business context", "Objective", "Options",
                "Decision criteria", "Evidence", "Assumptions", "Tradeoffs", "Risks",
                "Expected outcomes", "Recommendation and decision guidance",
                "Uncertainty, limitations and next steps")


def render(result):
    """The package as markdown, formatted once. Adds no sentence of analysis."""
    record = result.as_dict() if isinstance(result, DecisionResult) else result
    body = record["body"]
    options = dict((o["option_id"], o) for o in body["options"])
    criteria = dict((c["criterion_id"], c) for c in body["criteria"])
    lines = ["# Decision support — %s" % (record.get("subject") or "subject not stated"), "",
             "**Lifecycle:** %s — %s" % (record["lifecycle"], record["verification"]),
             "_%s_" % record["lifecycle_note"], "",
             "> %s" % record["human_decision"], "", "_%s_" % record["order_note"], ""]

    def label(option_id):
        return options[option_id]["label"]

    def reasons(entry):
        return (" — %s" % ", ".join(entry["confidence_reasons"])
                if entry["confidence_reasons"] else "")

    for number, (key, title) in enumerate(zip(PART_ORDER, _PART_TITLES), start=1):
        lines += ["## %d. %s" % (number, title), ""]
        part = body[key]
        if key == "decision_question":
            lines.append("%s _(the user's question)_" % part["text"])
        elif key == "business_context":
            lines.append("Subject: %s · Business model: %s · Currency: %s"
                         % (part["subject"] or "not stated",
                            part["business_model"] or "not stated",
                            part["currency"] or "not stated"))
            lines += ["- Constraint _(user)_: %s" % c["text"] for c in part["constraints"]]
        elif key == "objective":
            lines.append("%s _(the user's objective)_" % part["text"] if part["stated"]
                         else "_Not stated._")
        elif key == "options":
            lines += ["- %s _(%s)_" % (o["label"], o["origin"].replace("_", " ")) for o in part]
        elif key == "criteria":
            lines += ["- %s _(%s%s)_" % (c["text"], c["origin"],
                                         ", " + c["source"] if c["source"] else "")
                      for c in part] or ["_None stated — no option can be preferred._"]
        elif key == "evidence":
            lines += ["- `%s` [%s · %s · %s · %s] %s" % (
                d["synthesis_id"], d["kind"], d["domain"], d["support"], d["confidence"],
                d["statement"]) for d in part]
        elif key == "assumptions":
            lines += ["- `%s` %s _(assumed; never evidence)_" % (a["synthesis_id"],
                                                                 a["statement"])
                      for a in part] or ["_None._"]
        elif key == "tradeoffs":
            lines += ["- %s: %s _(reading; confidence %s%s; evidence %s)_" % (
                " vs ".join(label(o) for o in t["option_ids"]), t["text"], t["confidence"],
                reasons(t), ", ".join("`%s`" % e for e in t["evidence"]))
                for t in part] or ["_None._"]
        elif key == "risks":
            lines += ["- %s: %s _(%s; confidence %s%s)_" % (
                label(r["option_id"]), r["text"],
                "evidence " + ", ".join("`%s`" % e for e in r["evidence"]) if r["evidence"]
                else "unevidenced", r["confidence"], reasons(r)) for r in part] or ["_None._"]
        elif key == "expected_outcomes":
            lines += ["- %s: %s _(evidence %s; confidence %s%s)_" % (
                label(o["option_id"]), o["text"],
                ", ".join("`%s`" % e for e in o["evidence"]), o["confidence"], reasons(o))
                for o in part] or ["_None._"]
        elif key == "guidance":
            for rec in part["recommendations"]:
                lines.append("- `%s` _(%s)_ **%s** — confidence %s%s" % (
                    rec["recommendation_id"], rec["issued_by"], rec["action"],
                    rec["confidence"], reasons(rec)))
            if part["preferred_option"]:
                basis = part["preference_basis"]
                held = [r for r in part["recommendations"]
                        if r["recommendation_id"] == basis["recommendation_id"]][0]
                lines.append("**Preferred option:** %s — against %s, on record `%s`, carrying "
                             "that record's confidence %s%s. The other options are not ordered."
                             % (label(part["preferred_option"]),
                                "; ".join(criteria[c]["text"] for c in basis["criterion_ids"]),
                                basis["recommendation_id"], held["confidence"], reasons(held)))
            else:
                lines.append("**No preferred option.** %s" % part["no_preference_reason"])
            lines += ["- Divergence between %s: %s" % (", ".join("`%s`" % r for r in
                                                                 d["recommendation_ids"]),
                                                       d["note"])
                      for d in part["divergences"]]
        elif key == "uncertainty":
            lines.append("**Package confidence:** %s%s" % (part["confidence"], reasons(part)))
            lines += ["- %s: %s%s" % (label(o["option_id"]), o["confidence"], reasons(o))
                      for o in part["options"]]
            lines += ["- Conflict `%s`: %s" % (c["conflict_id"], c.get("reason") or "")
                      for c in part["conflicts"]]
            lines += ["- Limitation `%s` %s — %s" % (l["code"], l.get("subject") or "",
                                                     l.get("reason") or "")
                      for l in part["limitations"]]
            lines += ["- Unresolved `%s` %s (%s)" % (u["synthesis_id"], u["dimension"],
                                                     u["reason"])
                      for u in part["unresolved_dimensions"]]
            lines += ["- Next step _(evidence gap, not an action)_: %s — addresses %s `%s`"
                      % (n["text"], n["addresses"]["kind"], n["addresses"]["ref"])
                      for n in part["next_steps"]]
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "build", "render", "DecisionResult", "DecisionSupportError",
    "SCHEMA_VERSION", "ANALYSIS", "ISSUED_BY", "DRAFT", "FINAL", "LIFECYCLES", "UNVERIFIED",
    "PRODUCES_FINAL", "EXECUTES_ACTIONS", "LIFECYCLE_NOTE", "HUMAN_DECISION", "ORDER_NOTE",
    "STATUS_QUO_LABEL", "PART_ORDER", "REQUEST_FIELDS", "MATERIALITY_KEYS", "NOT_ASSESSABLE",
    "NO_PREFERENCE_REQUESTED", "NO_PREFERENCE_CRITERIA", "NO_PREFERENCE_BASIS",
    "NO_PREFERENCE_RECORD", "NO_PREFERENCE_UNRELATED", "NO_PREFERENCE_UNASSESSED",
]
