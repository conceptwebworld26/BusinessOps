"""The disclosure gate: the one place that decides whether anything may leave the machine.

There is exactly one of these, and everything downstream depends on that being true. The
gate runs at query construction, before any tool call, and `retrieval.py` accepts only its
output - so "did the gate run?" is not a question a caller can get wrong by forgetting.

It does not implement privacy policy. The Milestone 3 primitives already decide whether an
aggregate may be disclosed, and `assess_disclosure` already joins the class-to-tier rule to
the four ADR-0009 checks. This module supplies the things a *query* has and an aggregate
does not - a destination, an approval, an operation, and the text that would actually be
transmitted - and then defers. A second privacy policy here would be a second thing to keep
correct, and the two would drift.

Three decision states, from ADR-0009:

    ALLOW                 Tier 0 or Tier 1; nothing further required
    ALLOW_WITH_APPROVAL   Tier 2; the user sees the exact text and approves this disclosure
    REFUSE                Tier 3, or a check failed, or ambiguity that cannot resolve down

Ambiguity resolves **upward in strictness**: an uncertain tier becomes the stricter one, an
unresolved sensitivity refuses, an unknown destination refuses. Every refusal offers the
Tier 0 alternative where one exists, and states it as a description - never by echoing the
value it just refused to send.
"""

import weakref

from .. import privacy as privacy_mod
from ..errors import ConsentRequiredError
from ..privacy import aggregation as aggregation_mod
from . import boundary as boundary_mod, contract as contract_mod, query as query_mod

# -- decision states ---------------------------------------------------------

ALLOW = "ALLOW"
ALLOW_WITH_APPROVAL = "ALLOW_WITH_APPROVAL"
REFUSE = "REFUSE"

DECISIONS = (ALLOW, ALLOW_WITH_APPROVAL, REFUSE)


class _Issuer(object):
    """The capability that authorises minting a decision. One instance, module-private.

    "Retrieval requires a `DisclosureDecision`" is a type check, and a type check is not a
    security control: any caller could construct the type. What retrieval actually needs to
    know is that **this gate ran and produced this authorisation**, which is a statement
    about provenance, not shape. Requiring an object only this module holds makes the
    success state unmintable from outside it.
    """

    __slots__ = ()


#: Held only by this module. `assess()` passes it; nothing else can.
_ISSUE = _Issuer()

#: Every decision this gate actually issued. Weak, so decisions are collected normally.
#: The registry is what defeats `object.__new__(DisclosureDecision)` - an object that
#: skipped `__init__` never entered it, so it is not something the gate issued, whatever
#: its type says.
_ISSUED = weakref.WeakSet()


def is_gate_issued(decision):
    """Whether this exact object was minted by `assess()`. Identity, not shape."""
    try:
        return decision in _ISSUED
    except TypeError:                       # unhashable - certainly not one of ours
        return False


def _issue(*args, **kwargs):
    """Mint a decision and register it. The only function that writes to `_ISSUED`.

    Registration is separated from construction on purpose. If both lived in `__init__`,
    obtaining the issuance capability would be enough to mint an object the registry
    vouches for. Split, an attacker needs the capability *and* write access to the
    registry - two distinct deliberate acts against two named private controls, at which
    point they are editing this module rather than calling it, and no design defends
    against that.
    """
    decision = DisclosureDecision(*args, _issuer=_ISSUE, **kwargs)
    _ISSUED.add(decision)
    return decision


class DisclosureDecision:
    """The gate's verdict: a gate-issued, immutable authorisation.

    Three properties, and retrieval depends on all three rather than on the type alone:

    **Issued.** `__init__` requires the module-private issuance capability, and every
    genuine decision is registered in `_ISSUED`. A forged object - constructed directly,
    subclassed, or built with `object.__new__` to skip `__init__` - is not in the registry
    and is refused by `RetrievalRequest`.

    **Immutable.** Once issued, every attribute is read-only. A refusal cannot be edited
    into an ALLOW, a tier cannot be lowered, and an approval cannot be assigned around
    `authorise()`. `authorise()` is the single controlled exception and validates before it
    writes.

    **Bound.** The exact text, destination and tier that were *assessed* are captured at
    issue. `query_text` returns the bound text, not whatever the query object currently
    says, and `authorised` re-checks that the query has not been altered since. Mutating a
    `CandidateQuery` after assessment therefore does not change what may be sent; it
    invalidates the authorisation, which is the safe direction to fail.
    """

    __slots__ = ("decision", "tier", "requested_tier", "query", "destination", "request",
                 "reasons", "failed_checks", "assessments", "alternative",
                 "operation", "_bound_text", "_bound_destination", "_bound_tier",
                 "_approval", "_issued", "__weakref__")

    def __init__(self, decision, tier, requested_tier, query, destination, request,
                 reasons=(), failed_checks=(), assessments=(), alternative=None,
                 approval=None, operation=None, _issuer=None):
        if _issuer is not _ISSUE:
            raise contract_mod.ResearchError(
                "a DisclosureDecision is issued by gate.assess(); it cannot be "
                "constructed directly. Retrieval accepts only an authorisation this gate "
                "produced, so building one by hand would be a gate bypass.")
        if decision not in DECISIONS:
            raise contract_mod.ResearchError("unknown disclosure decision %r" % (decision,))

        self.decision = decision
        self.tier = tier
        self.requested_tier = requested_tier
        self.query = query
        self.destination = destination
        self.request = request
        self.reasons = list(reasons)
        self.failed_checks = list(failed_checks)
        self.assessments = list(assessments)
        self.alternative = alternative
        self.operation = operation

        # What was actually assessed. Captured now so later mutation of the query or the
        # destination object cannot change what this authorisation covers.
        self._bound_text = query.text if query is not None else None
        self._bound_destination = (destination.identity()
                                   if destination is not None else None)
        self._bound_tier = tier
        # Approval is never accepted at construction: ADR-0010 requires it to be explicit,
        # and `authorise()` is where it is checked against the binding.
        self._approval = None

        # Deliberately NOT registered here. Registration is `_issue()`'s job, so the
        # issuance capability and the registry are two separate controls: holding one is
        # not holding the other.
        self._issued = True

    # -- immutability -------------------------------------------------------

    def __setattr__(self, name, value):
        if getattr(self, "_issued", False):
            raise contract_mod.ResearchError(
                "a disclosure decision is immutable once issued; %r cannot be changed. "
                "Re-run gate.assess() to obtain a decision for different terms." % name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise contract_mod.ResearchError(
            "a disclosure decision is immutable once issued; %r cannot be deleted." % name)

    # -- binding ------------------------------------------------------------

    @property
    def binding_intact(self):
        """Whether the query and destination still match what was assessed."""
        current_text = self.query.text if self.query is not None else None
        current_destination = (self.destination.identity()
                               if self.destination is not None else None)
        return (current_text == self._bound_text
                and current_destination == self._bound_destination
                and self.tier == self._bound_tier)

    @property
    def approval(self):
        """Read-only. `authorise()` is the only way to attach one."""
        return self._approval

    @property
    def authorised(self):
        """Whether retrieval may proceed on this decision alone.

        Requires the binding to be intact *and* the gate to have issued this object, so a
        tampered or forged decision reports False rather than authorising anything.
        """
        if not is_gate_issued(self) or not self.binding_intact:
            return False
        if self.decision == ALLOW:
            return True
        if self.decision == ALLOW_WITH_APPROVAL:
            return bool(self._approval and self._approval.matches(
                self._bound_text, self.destination))
        return False

    @property
    def query_text(self):
        """The text that was assessed - not whatever the query object now says."""
        return self._bound_text

    @property
    def refused(self):
        return self.decision == REFUSE

    def consent_request(self):
        """Exactly what the user is being asked to approve (ADR-0010 shape)."""
        if self.decision != ALLOW_WITH_APPROVAL:
            return None
        return {
            "action": "send an external research query containing derived business context",
            "transmitted_text": self.query_text,
            "destination": self.destination.as_dict(),
            "tier": self.tier,
            "why_approval_is_needed": "; ".join(self.reasons) or None,
            "single_use": True,
            "session_wide": False,
            "if_declined": (self.alternative or {}).get("explanation"),
            "alternative_query": (self.alternative or {}).get("text"),
        }

    def authorise(self, approval):
        """Attach an approval. The single controlled write to an otherwise frozen object.

        Validates before it writes, and writes through `object.__setattr__` because the
        instance is immutable by design - this is the one path allowed to set an approval,
        which is what stops `decision.approval = ...` from being an authorisation route.
        """
        if not is_gate_issued(self):
            raise contract_mod.ResearchError(
                "this decision was not issued by the disclosure gate and cannot be "
                "authorised")
        if self.decision != ALLOW_WITH_APPROVAL:
            raise contract_mod.ResearchError(
                "only an ALLOW_WITH_APPROVAL decision can be authorised; this one is %s"
                % self.decision)
        if not self.binding_intact:
            raise contract_mod.ResearchError(
                "the query or destination has been altered since this decision was "
                "issued; re-run gate.assess() rather than authorising a changed request")
        if approval is None or not approval.granted:
            raise ConsentRequiredError(
                "send an external research query", detail=self.query_text)
        if not approval.matches(self._bound_text, self.destination):
            raise contract_mod.ResearchError(
                "this approval does not authorise this disclosure: approval is per query "
                "and per destination, single-use, and never session-wide")
        object.__setattr__(self, "_approval", approval)
        return self

    def as_dict(self):
        record = {
            "decision": self.decision, "tier": self.tier,
            "requested_tier": self.requested_tier,
            "authorised": self.authorised,
            "transmitted_text": self.query_text,
            "destination": self.destination.as_dict() if self.destination else None,
            "operation": self.operation,
            "reasons": list(self.reasons), "failed_checks": list(self.failed_checks),
            "assessments": [a.as_dict() for a in self.assessments],
            "alternative": self.alternative,
        }
        return {k: v for k, v in record.items() if v not in (None, [], {})}

    def __repr__(self):
        return "DisclosureDecision(%s, tier=%s)" % (self.decision, self.tier)


def _refuse(request, candidate, reason_code, explanation, alternative=None,
            failed=(), assessments=(), reasons=()):
    return _issue(
        REFUSE, None, request.requested_tier, candidate, request.destination, request,
        reasons=list(reasons) or [explanation],
        failed_checks=list(failed) or [reason_code],
        assessments=assessments, alternative=alternative, operation=request.operation)


def assess(request, accumulator=None, k_floor=None, as_of=None):
    """Decide whether this research request may be sent. The authoritative decision.

    `accumulator` is the active operation's `DisclosureAccumulator`. When supplied,
    re-identification is judged against everything already disclosed in the operation
    rather than this query alone, so a sequence of individually safe queries cannot become
    collectively identifying.

    Nothing is recorded on the accumulator here - a decision is not a disclosure. The
    caller records after retrieval actually happens, which is why `record_disclosure()`
    exists separately.
    """
    # 0. The internal-value register (ADR-0050): the workspace's business data, read by
    #    the gate itself. If it cannot be built, nothing can be vouched for, so nothing
    #    is sent - and no alternative is offered, because none can be checked either.
    try:
        register = boundary_mod.workspace_register()
    except boundary_mod.BoundaryUnverifiable as error:
        return _refuse(
            request, None, contract_mod.REASON_BOUNDARY_UNVERIFIABLE,
            "No research was performed. The business data in the working directory could "
            "not be screened, so the gate cannot confirm that this query carries no "
            "internal value: %s." % error)

    # 1. Structural validity. A malformed or prohibited request never reaches the
    #    privacy layer, because some of its contents must not be inspected at all.
    problems = request.validate()
    if problems:
        reason_code, explanation = problems[0]
        alternative = None
        if reason_code in (contract_mod.REASON_PROHIBITED_CONTENT,
                           contract_mod.REASON_UNRESOLVED_SENSITIVITY):
            alternative = _safe_alternative(request, register)
        return _refuse(request, None, reason_code, explanation, alternative,
                       failed=[code for code, _ in problems],
                       reasons=[text for _, text in problems])

    candidate = query_mod.build(request)

    # 1b. Provenance (ADR-0050). Every fragment of the request is screened against the
    #     register, whatever field carries it and whatever class the caller declared. A
    #     value from a `never` column has no path; any other internal value has only the
    #     Tier 2 one. Neither is ever Tier 0.
    findings = boundary_mod.screen(request, register)
    if findings:
        refusal = _internal_value_decision(request, candidate, findings, register)
        if refusal is not None:
            return refusal

    # 2. Destination. An unrecognised provider is refused rather than attempted.
    if not request.destination.permitted:
        return _refuse(
            request, candidate, contract_mod.REASON_DESTINATION_NOT_PERMITTED,
            "Destination %r is not a permitted retrieval destination. BusinessOps "
            "retrieves from the public web only." % request.destination.identity())

    # 3. Tier 0: no internal value is transmitted, so there is nothing to assess.
    #    Checked before the aggregate machinery because a Tier 0 query has no aggregates
    #    and running an aggregate assessment over an empty list would invent a verdict.
    if not request.derived_context:
        if request.requested_tier != 0:
            # Asking for a higher tier while disclosing nothing is not an error, but the
            # gate does not honour an inflated request: the effective tier is what the
            # query actually discloses.
            pass
        return _issue(
            ALLOW, 0, request.requested_tier, candidate, request.destination, request,
            reasons=["No internal value is transmitted: the query is built only from "
                     "public terms, and any comparison is computed locally."],
            operation=request.operation)

    # 4. Derived context present. Every value must independently clear the tier.
    if request.requested_tier == 0:
        return _refuse(
            request, candidate, contract_mod.REASON_TIER_NOT_PERMITTED,
            "The request carries derived business context but asks for Tier 0, which "
            "transmits nothing internal. A Tier 0 request is not silently promoted.",
            alternative=_safe_alternative(request, register))

    effective_k = aggregation_mod.resolve_k_floor(k_floor)
    assessments, reasons, failed = [], [], []

    for descriptor in request.derived_context:
        assessment = aggregation_mod.assess_disclosure(
            descriptor, k_floor=effective_k,
            query_attributes=candidate.narrowing_attributes,
            accumulated=accumulator)
        assessments.append(assessment)
        reasons.extend(assessment.reasons)
        if not assessment.permitted:
            failed.extend(assessment.failed_checks)

    if failed:
        # Tier 1 refused. Tier 2 is the governed path for the remainder - unless what
        # failed can never be approved, in which case there is no path at all.
        unapprovable = _unapprovable(failed, request)
        alternative = _safe_alternative(request, register)
        if unapprovable:
            return _refuse(
                request, candidate, unapprovable[0], unapprovable[1], alternative,
                failed=failed, assessments=assessments, reasons=reasons)

        if request.requested_tier < 2:
            return _refuse(
                request, candidate, contract_mod.REASON_TIER_NOT_PERMITTED,
                "The derived context does not qualify for Tier 1, and Tier 2 was not "
                "requested. Raise the request to Tier 2 to be shown the exact text and "
                "approve it, or use the Tier 0 alternative.",
                alternative, failed=failed, assessments=assessments, reasons=reasons)

        return _issue(
            ALLOW_WITH_APPROVAL, 2, request.requested_tier, candidate,
            request.destination, request,
            reasons=reasons + ["Tier 1 checks did not pass, so this disclosure requires "
                               "explicit per-query approval."],
            failed_checks=failed, assessments=assessments, alternative=alternative,
            operation=request.operation)

    # 5. Tier 1 permitted. The tier is the strictest any single value required.
    tier = max((a.tier for a in assessments if a.tier is not None), default=1)
    return _issue(
        ALLOW, tier, request.requested_tier, candidate, request.destination, request,
        reasons=reasons, assessments=assessments, operation=request.operation)


def _internal_value_decision(request, candidate, findings, register):
    """The decision for a request that carries internal material. Never ALLOW.

    Returns a REFUSE or an ALLOW_WITH_APPROVAL. The explanation says what was found and
    where - field, column, file - and never repeats the value, and it says in terms that
    this is a privacy block: no research ran, which is not the same as no source existing.
    """
    strictest = boundary_mod.strictest(findings)
    where = "; ".join(f.describe() for f in findings)
    alternative = _boundary_alternative(request, findings, register,
                                        approvable=strictest != privacy_mod.NEVER)
    failed = ["internal_business_value"]
    # Approval covers the query text the user is shown, and nothing else. A value in the
    # operation id, the destination or a note would travel, or be recorded, unseen, so it
    # has no approval path even where the same value in the query would have one.
    outside_text = [f for f in findings if not f.in_query_text]
    if outside_text and strictest != privacy_mod.NEVER:
        return _refuse(
            request, candidate, contract_mod.REASON_INTERNAL_VALUE,
            "Internal business data cannot be sent to external research. No research was "
            "performed: %s. Identifiers and request metadata never carry internal values, "
            "and approval covers only the query text, so there is no approval path. This "
            "is a privacy block, not a finding that no public source exists."
            % "; ".join(f.describe() for f in outside_text),
            alternative, failed=failed)
    if strictest == privacy_mod.NEVER:
        return _refuse(
            request, candidate, contract_mod.REASON_INTERNAL_VALUE,
            "Internal business data cannot be sent to external research. No research was "
            "performed, and no approval can release this value (Tier 3): %s. This is a "
            "privacy block, not a finding that no public source exists." % where,
            alternative, failed=failed)
    if request.requested_tier < 2:
        return _refuse(
            request, candidate, contract_mod.REASON_INTERNAL_VALUE,
            "Internal business data cannot be sent to external research at Tier %s. No "
            "research was performed: %s. It could be sent only at Tier 2, after you see "
            "the exact text and approve this one query; otherwise use the public-terms "
            "alternative. This is a privacy block, not a finding that no public source "
            "exists." % (request.requested_tier, where),
            alternative, failed=failed)
    return _issue(
        ALLOW_WITH_APPROVAL, 2, request.requested_tier, candidate, request.destination,
        request,
        reasons=["The query carries internal business data (%s), so it requires explicit "
                 "per-query approval of the exact text." % where],
        failed_checks=failed, alternative=alternative, operation=request.operation)


_ALTERNATIVE_EXPLANATION = (
    "Research the industry, market or product category in public terms only, and compare "
    "locally. Where a public company is itself the subject, name it as the research "
    "subject; internal context can travel only as a banded, aggregated descriptor that "
    "passes the Tier 1 checks.")


def _boundary_alternative(request, findings, register, approvable=False):
    """The public-terms query left once every flagged fragment is removed, vetted again."""
    flagged = {f.field for f in findings}
    flagged_keys = {f.term_key for f in findings if f.term_key is not None}
    terms = {key: value for key, value in query_mod.safe_public_terms(
        request.public_terms).items() if key not in flagged_keys}
    stripped = contract_mod.ResearchRequest(
        subject="" if "subject" in flagged else request.subject,
        category=request.category, intent=request.intent, public_terms=terms,
        derived_context=(), requested_tier=0, destination=request.destination)
    text = query_mod.build(stripped).text
    intent_only = text.strip().lower() == str(
        query_mod.INTENT_TERMS.get(request.intent) or "").strip().lower()
    if not text.strip() or intent_only or not boundary_mod.text_is_clean(text, register):
        text = None
    explanation = _ALTERNATIVE_EXPLANATION
    if not approvable:
        explanation = "No approval releases the internal value. " + explanation
    if text is None:
        explanation += (" No public term in this request survives the screen, so name the "
                        "industry, market or public company to research.")
    return {"text": text, "tier": 0, "explanation": explanation}


def _safe_alternative(request, register):
    """`query.tier_zero_alternative`, unless its text carries internal material.

    The Tier 0 alternative keeps the subject, and a subject can itself be internal. An
    alternative that repeated the customer name it replaced would leak through the very
    message meant to protect it.
    """
    alternative = query_mod.tier_zero_alternative(request)
    if boundary_mod.text_is_clean(alternative["text"], register):
        findings = boundary_mod.screen(request, register)
        if not any(f.field == "subject" for f in findings):
            return alternative
    return _boundary_alternative(request, boundary_mod.screen(request, register), register)


def _unapprovable(failed, request):
    """Failures that no approval can unlock. Returns (reason_code, explanation) or None."""
    if "never_externalizable" in failed:
        return (contract_mod.REASON_PROHIBITED_CONTENT,
                "The request rests on data classified `never`, which has no approval path "
                "at any tier. It is refused rather than escalated.")
    if "sensitivity_unresolved" in failed:
        return (contract_mod.REASON_UNRESOLVED_SENSITIVITY,
                "The sensitivity of one or more values was never established. An "
                "unclassified value is not assumed safe and cannot be approved into "
                "safety; classify it first.")
    if "aggregation_floor" in failed:
        return (contract_mod.REASON_AGGREGATION_FLOOR,
                "An aggregate below the k-anonymity floor can expose an individual. The "
                "floor is a hard minimum and no approval lowers it; aggregate over more "
                "entities or use the Tier 0 alternative.")
    return None


def record_disclosure(decision, accumulator):
    """Record an *actually made* disclosure against the active operation.

    Called after retrieval, not after the decision: a refused or unapproved query
    disclosed nothing, and counting it would tighten the gate on the strength of
    information that never left the machine.
    """
    if accumulator is None or decision is None:
        return accumulator
    if not decision.authorised:
        return accumulator
    if decision.query is not None:
        accumulator.record(decision.query.narrowing_attributes)
    return accumulator


def ledger_entry(decision):
    """The disclosure record for the evidence ledger.

    ADR-0009 requires the decision *and the transmitted text* to be auditable, including
    refusals - a reviewer needs to see what was not sent as much as what was.
    """
    return {
        "kind": "disclosure_decision",
        "decision": decision.decision,
        "tier": decision.tier,
        "requested_tier": decision.requested_tier,
        "authorised": decision.authorised,
        "transmitted_text": decision.query_text if decision.authorised else None,
        "proposed_text": decision.query_text,
        "destination": decision.destination.as_dict() if decision.destination else None,
        "operation": decision.operation,
        "reasons": list(decision.reasons),
        "failed_checks": list(decision.failed_checks),
        "alternative_offered": bool(decision.alternative),
    }
