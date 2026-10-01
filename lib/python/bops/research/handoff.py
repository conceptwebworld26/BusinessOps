"""The two Python halves of a model-mediated retrieval, in the order a caller needs them.

`scout.py` holds the boundary types. This module holds the pair of calls an orchestration
surface actually makes, because the middle leg of a retrieval is not Python's to perform:

    open_retrieval()    request -> query -> GATE -> authorisation -> brief   (what goes out)
        ...  the model dispatches `businessops:bops-research-scout`, which searches  ...
    close_retrieval()   envelope -> parse -> normalise -> EvidenceSet         (what comes in)

Both return plain JSON-serialisable dicts, because the caller is a markdown command reading
stdout rather than a Python program holding objects.

**The gate runs in both halves, on purpose.** The two calls are separate processes, so no
authorisation survives between them; `close_retrieval` therefore re-derives the decision
from the same request rather than being handed one. That is the safe direction: evidence
cannot be assembled for a request the gate would not have approved, and there is no token,
handle or serialised authorisation for a caller to forge in between. The cost is that the
request parameters must be identical in both calls, which is deterministic and cheap.

This module adds no policy. It sequences `query`, `gate`, `retrieval` and `scout`, all of
which already own their rules.
"""

from . import contract as contract_mod
from . import gate as gate_mod
from . import retrieval as retrieval_mod
from . import scout as scout_mod
from . import sources as sources_mod

#: What `open_retrieval` reports when the gate did not allow the query out.
NOT_AUTHORISED = "not_authorised"

#: What it reports when a brief exists and the scout may be dispatched.
AUTHORISED = "authorised"

# -- candidate claims --------------------------------------------------------
#
# The `EvidenceSet` is the authoritative output of a retrieval. A candidate claim is a
# **derived, intermediate, unverified** reading of one evidence item, and the distinction is
# load-bearing: an evidence item records that a source said something, while a claim records
# that we are asserting it. Nothing in M9-B verifies a claim, so every claim produced here
# carries its candidacy in the record rather than in a convention someone must remember.

#: Marks every claim this module produces. There is deliberately no "verified" value: no
#: code path in M9-B can promote a candidate, so a constant naming that state would exist
#: only to be misused.
CANDIDATE = "candidate"

#: Longest statement accepted. A claim longer than this is a paragraph, and a paragraph is
#: where unsupported inference hides.
MAX_STATEMENT_CHARS = 400

#: Language that turns a report of what a source said into advice or an impact judgement.
#: This is a **guard, not a proof** - it catches the obvious cases mechanically so that the
#: reviewer's attention is left for the ones that need judgement. The substantive obligation
#: ("do not broaden the source's statement") is stated to the model in
#: `commands/retrieval-slice.md`, because no string check can decide whether a sentence
#: exceeds its source.
ADVISORY_MARKERS = (
    "we should", "you should", "we recommend", "i recommend", "recommend that",
    "must ", "ought to", "the business should", "suggests we", "implies we",
    "therefore we", "this means we", "opportunity to", "risk to our", "for us this",
)


def _request(subject, category, **kwargs):
    """Build the `ResearchRequest` both halves derive from. No defaults invented here."""
    return contract_mod.ResearchRequest(subject, category, **kwargs)


def _decide(subject, category, **kwargs):
    request = _request(subject, category, **kwargs)
    return request, gate_mod.assess(request)


def _refusal(decision):
    """A refusal or a pending approval, rendered for a caller that only reads stdout.

    The decision renders itself. Re-describing a refusal here would be a second account of
    it, and the gate's own account is the one the ledger records.
    """
    record = decision.as_dict()
    return {
        "status": NOT_AUTHORISED,
        "decision": decision.decision,
        "tier": decision.tier,
        "reasons": list(decision.reasons),
        "failed_checks": list(decision.failed_checks),
        "explanation": "; ".join(decision.reasons) or "The gate did not authorise this "
                                                      "query.",
        "alternative": record.get("alternative"),
        "ledger_entry": gate_mod.ledger_entry(decision),
        "brief": None,
        # Stated, not implied: a refusal is not an empty search. A caller that reports
        # "no reliable source found" here has misread a privacy block as a result.
        "research_performed": False,
    }


def open_retrieval(subject, category, max_results=scout_mod.MAX_RESULTS,
                   max_fetched=scout_mod.MAX_FETCHED,
                   timeout_seconds=scout_mod.DEFAULT_TIMEOUT_SECONDS, **kwargs):
    """Run the gate and, if it authorised the query, return the brief that may be sent.

    The returned `brief` is exactly `ScoutBrief.as_dict()` - the six fields and nothing
    else. A caller that dispatches anything other than this dict has left the boundary,
    which is why the dict is the whole of the return value rather than one field of a
    larger context object.

    **No return-protocol field is advertised here.** Until M9-C.17 this returned
    `envelope_expected: bops.scout.result/1`, naming the bare-envelope contract ADR-0017
    superseded. Nothing consumed it and it never reached a scout - the brief is the whole
    scout payload - but production output naming a retired contract is a defect whatever
    reads it, so it was removed rather than re-pointed. The scout's return contract lives
    in `agents/bops-research-scout.md` and ADR-0017; `close_retrieval` enforces it.
    """
    request, decision = _decide(subject, category, **kwargs)
    if not decision.authorised:
        return _refusal(decision)

    brief = scout_mod.ScoutBrief(
        retrieval_mod.RetrievalRequest(decision), max_results=max_results,
        max_fetched=max_fetched, timeout_seconds=timeout_seconds)
    return {
        "status": AUTHORISED,
        "decision": decision.decision,
        "tier": decision.tier,
        "agent": "businessops:bops-research-scout",
        "ledger_entry": gate_mod.ledger_entry(decision),
        "brief": brief.as_dict(),
    }


def _refuse_claim(proposal, reason, explanation):
    return {"status": "not_produced", "reason": reason, "explanation": explanation,
            "evidence_id": proposal.get("evidence_id"),
            "statement": str(proposal.get("statement") or "")[:MAX_STATEMENT_CHARS]}


#: Longest free-text field accepted on a conflict proposal. A reason is a sentence; a
#: paragraph is a report, and a report is not metadata about evidence.
MAX_CONFLICT_TEXT_CHARS = 400

#: Fields a caller may supply on one position. `source`, `source_tier`, `source_date` and
#: `freshness` are deliberately **absent**: they are read from the evidence item the
#: position points at. A proposer that could name a tier could promote a content farm by
#: asserting one, which is the attack `sources.classify_tier` exists to prevent.
ACCEPTED_POSITION_FIELDS = frozenset({"evidence_id", "value", "unit", "definition", "scope"})

MIN_CONFLICT_POSITIONS = 2


def _refuse_conflict(proposal, reason, explanation):
    subject = proposal.get("subject") if isinstance(proposal, dict) else None
    return {"status": "not_recorded", "reason": reason, "explanation": explanation,
            "subject": _clean_text(subject)}


def _clean_text(value, limit=MAX_CONFLICT_TEXT_CHARS):
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _position(raw, by_id):
    """Build one `SourcePosition` from a proposal entry. Returns `(position, problem)`.

    Source identity, tier, date and freshness come from the **evidence item**, never from
    the proposal. The caller says which item and what that item's figure was; everything
    that confers authority is looked up locally.
    """
    if not isinstance(raw, dict):
        return None, "a conflict position must be a record"

    unknown = sorted(set(raw) - ACCEPTED_POSITION_FIELDS)
    if unknown:
        return None, ("a conflict position accepts only %s; %s is not transportable"
                      % (", ".join(sorted(ACCEPTED_POSITION_FIELDS)), ", ".join(unknown)))

    evidence_id = raw.get("evidence_id")
    if not evidence_id or not isinstance(evidence_id, str):
        return None, "a conflict position must name the evidence item it comes from"

    item = by_id.get(evidence_id)
    if item is None:
        return None, ("no evidence item in this set carries id %r; a conflict cannot be "
                      "recorded against evidence that was not retrieved" % evidence_id)

    value = raw.get("value")
    if isinstance(value, (list, tuple, set, dict)):
        return None, "a conflict position's value must be a single figure or phrase"
    if value is None or str(value).strip() == "":
        return None, "a conflict position must carry what that source actually said"

    return sources_mod.SourcePosition(
        evidence_id=item.id,
        value=value if isinstance(value, (int, float)) else _clean_text(value),
        source=item.source,
        source_tier=item.source_tier,
        source_date=item.publication_date,
        unit=_clean_text(raw.get("unit"), 40),
        definition=_clean_text(raw.get("definition")),
        scope=_clean_text(raw.get("scope")),
        # `item.freshness` is the full assessment record; a position carries the verdict.
        freshness=item.freshness.get("freshness"),
    ), None


def _structured_conflicts(evidence, conflicts):
    """Record conflicts the research layer observed. Returns the refusals.

    This is the M9-C.4 transport (ADR-0016). It is deliberately the mirror of
    `_candidate_claims`: the model supplies judgement - *these two sources disagree about
    this* - and Python supplies validation and every field that carries authority.

    Python never decides that a conflict exists. It decides only whether a declared one is
    **transportable**: a subject, two or more positions, and every position tied to an item
    already in this set. Prose is not a conflict, a single position is not a disagreement,
    and an unknown evidence id is refused rather than created.
    """
    refused = []
    by_id = {item.id: item for item in evidence.items}

    for proposal in conflicts or []:
        if not isinstance(proposal, dict):
            refused.append(_refuse_conflict({}, "malformed_conflict",
                                            "A conflict must be a record."))
            continue

        subject = _clean_text(proposal.get("subject"))
        if not subject:
            refused.append(_refuse_conflict(
                proposal, "no_subject",
                "A conflict must name what the sources disagree about."))
            continue

        raw_positions = proposal.get("positions")
        if not isinstance(raw_positions, (list, tuple)):
            refused.append(_refuse_conflict(
                proposal, "malformed_positions",
                "A conflict must carry a list of positions, one per disagreeing source."))
            continue
        if len(raw_positions) < MIN_CONFLICT_POSITIONS:
            refused.append(_refuse_conflict(
                proposal, "insufficient_positions",
                "A conflict needs at least %d positions; one source cannot disagree with "
                "itself." % MIN_CONFLICT_POSITIONS))
            continue

        positions, problem = [], None
        for raw in raw_positions:
            position, problem = _position(raw, by_id)
            if problem is not None:
                break
            positions.append(position)
        if problem is not None:
            refused.append(_refuse_conflict(proposal, "invalid_position", problem))
            continue

        if len({p.evidence_id for p in positions}) < MIN_CONFLICT_POSITIONS:
            refused.append(_refuse_conflict(
                proposal, "single_source",
                "Every position names the same evidence item. A source does not conflict "
                "with itself; report it once."))
            continue

        evidence.record_conflict(subject, positions, declared=True,
                                 reason=proposal.get("reason"))

    return refused


def _candidate_claims(evidence, proposals):
    """Turn proposed readings of evidence into candidate claims, or explain each refusal.

    A proposal is `{"evidence_id": ..., "statement": ..., "material": bool}`. The statement
    is the model's reading of one item, because deciding what a source says is judgement and
    Python does not have any. What Python does have is the policy, and it is applied here
    rather than trusted: the item must be in **this** set, the tier rules must permit it, an
    unresolved conflict must not be papered over, and the language must not have turned into
    advice.

    A refusal is a result, not an error. `candidate_claim: NOT PRODUCED` is the correct
    outcome whenever the evidence does not support one, and is never worked around.
    """
    produced, refused = [], []
    by_id = {item.id: item for item in evidence.items}
    conflicted = evidence.has_conflict()

    for proposal in proposals or []:
        if not isinstance(proposal, dict):
            refused.append(_refuse_claim({}, "malformed_proposal",
                                         "A claim proposal must be a record."))
            continue

        statement = str(proposal.get("statement") or "").strip()
        if not statement:
            refused.append(_refuse_claim(proposal, "no_statement",
                                         "A claim with no statement is not a claim."))
            continue
        if len(statement) > MAX_STATEMENT_CHARS:
            refused.append(_refuse_claim(
                proposal, "statement_too_long",
                "A claim longer than %d characters is a paragraph; state one assertion."
                % MAX_STATEMENT_CHARS))
            continue

        lowered = statement.lower()
        marker = next((m for m in ADVISORY_MARKERS if m in lowered), None)
        if marker is not None:
            refused.append(_refuse_claim(
                proposal, "not_a_source_claim",
                "This reads as advice or an impact judgement (%r), not as a report of what "
                "the source said. Interpretation and recommendation are later layers and "
                "are not part of retrieval." % marker.strip()))
            continue

        item = by_id.get(proposal.get("evidence_id"))
        if item is None:
            refused.append(_refuse_claim(
                proposal, "untraceable",
                "No evidence item in this set carries that id. A claim that cannot be "
                "traced to retrieved evidence is not a candidate for one."))
            continue

        if conflicted:
            refused.append(_refuse_claim(
                proposal, "unresolved_conflict",
                "This set records sources that disagree. Conflicts are reported, never "
                "silently resolved or averaged, so no single-source claim stands here."))
            continue

        claim, failure = scout_mod.candidate_claim(
            item, statement, material=bool(proposal.get("material", True)))
        if failure is not None:
            refused.append(_refuse_claim(proposal, failure.reason, failure.explanation))
            continue

        record = claim.as_dict()
        # Candidacy, traceability and the item's own limitations travel with the claim,
        # so a consumer reading only the claim still cannot mistake it for a finding.
        record["status"] = CANDIDATE
        record["verified"] = False
        record["evidence_id"] = item.id
        record["material"] = bool(proposal.get("material", True))
        record["retrieved_at"] = item.retrieved_at
        record["freshness"] = item.freshness["freshness"]
        record["limitations"] = sorted(set(
            list(record.get("caveats") or [])
            + [n for n in item.notes if "tier was inferred" in n or "truncated" in n]
            + ["Candidate only: retrieved evidence is untrusted and this claim is "
               "unverified."]))
        produced.append(record)

    return produced, refused


def close_retrieval_object(payload, subject, category, as_of=None, proposals=None,
                           conflicts=None, max_results=scout_mod.MAX_RESULTS,
                           max_fetched=scout_mod.MAX_FETCHED,
                           timeout_seconds=scout_mod.DEFAULT_TIMEOUT_SECONDS, **kwargs):
    """`close_retrieval`, returning the live `EvidenceSet` under `evidence_set`.

    Same retrieval, same parsing, same local tiering, same conflicts - the only difference
    is that the set is handed back as the object rather than as `as_dict()`. It exists
    because `synthesis.register_external()` accepts **only** an `EvidenceSet` object, and
    deliberately so: a serialised set would carry `source_tier` as data, and a tier is
    something BusinessOps derives from the source rather than something it is told. Without
    this seam the only way into the synthesis layer was to drive `ScoutRetriever` by hand,
    which is a second assembly of the same pipeline and would drift from this one.

    There is no `evidence` key in the success result, and that is deliberate: a caller who
    means to serialise should call `close_retrieval`, and a key that is sometimes a record
    and sometimes an object is a key nobody can `json.dumps`. Failure and refusal results
    are returned exactly as `close_retrieval` produces them. See ADR-0024.
    """
    return _close(payload, subject, category, as_of=as_of, proposals=proposals,
                  conflicts=conflicts, max_results=max_results, max_fetched=max_fetched,
                  timeout_seconds=timeout_seconds, **kwargs)


def close_retrieval(payload, subject, category, as_of=None, proposals=None, conflicts=None,
                    max_results=scout_mod.MAX_RESULTS,
                    max_fetched=scout_mod.MAX_FETCHED,
                    timeout_seconds=scout_mod.DEFAULT_TIMEOUT_SECONDS, **kwargs):
    """Turn what the scout returned into an `EvidenceSet`, or into a structured failure.

    `payload` is **the scout's reply text** - the `BOPS-REC/1` / `BOPS-END/1` line protocol
    that ADR-0017 adopted as the production contract. It is untrusted input from here to the
    end: every line is checked against this retrieval's gate-bound operation, the declared
    count must match, records are stripped to the accepted fields, re-tiered locally, and
    marked `UNTRUSTED_EXTERNAL_DATA`.

    A **dict** is also accepted, and is the canonical envelope `parse_reply` builds
    internally. That path exists so fixtures and `ScoutTransport` can drive production
    normalisation directly; a scout cannot use it, because a scout reply is text. The
    superseded bare-envelope contract is therefore no longer reachable from a scout: JSON
    text is read as line protocol, finds no terminator, and fails closed.

    Returns the set **serialised**. A caller that needs the object - anything feeding
    `synthesis.register_external()` - calls `close_retrieval_object` instead; both run the
    same assembly, so the two cannot disagree.
    """
    result = _close(payload, subject, category, as_of=as_of, proposals=proposals,
                    conflicts=conflicts, max_results=max_results,
                    max_fetched=max_fetched, timeout_seconds=timeout_seconds, **kwargs)
    if "evidence_set" not in result:
        return result
    evidence = result.pop("evidence_set")
    result["evidence"] = evidence.as_dict()
    result["instruction_safe"] = evidence.as_instruction_safe_dict()
    return result


def _close(payload, subject, category, as_of=None, proposals=None, conflicts=None,
           max_results=scout_mod.MAX_RESULTS, max_fetched=scout_mod.MAX_FETCHED,
           timeout_seconds=scout_mod.DEFAULT_TIMEOUT_SECONDS, **kwargs):
    """The one assembly both public closers share. Returns the set as an object."""
    request, decision = _decide(subject, category, **kwargs)
    if not decision.authorised:
        return _refusal(decision)

    retrieval_request = retrieval_mod.RetrievalRequest(decision)
    brief = scout_mod.ScoutBrief(retrieval_request, max_results=max_results,
                                 max_fetched=max_fetched,
                                 timeout_seconds=timeout_seconds)

    # Text is what a scout sends, so text is the production contract. A dict is the internal
    # canonical envelope; see the docstring.
    if isinstance(payload, dict):
        records, failure = scout_mod.parse_result(payload, brief)
    else:
        records, failure = scout_mod.parse_reply(payload, brief)
    if failure is not None:
        return {"status": failure.status, "reason": failure.reason,
                "explanation": failure.explanation, "evidence": None,
                "brief": brief.as_dict()}

    normalised, rejected = scout_mod.normalise_records(records, brief, as_of=as_of)
    if not normalised:
        failure = contract_mod.failure(
            contract_mod.INSUFFICIENT_EVIDENCE, contract_mod.REASON_NO_ADEQUATE_SOURCE,
            "Retrieval returned nothing that could be cited. No reliable source found.",
            rejected=rejected)
        return {"status": failure.status, "reason": failure.reason,
                "explanation": failure.explanation, "rejected": rejected,
                "evidence": None, "brief": brief.as_dict()}

    # `_build_evidence` is the same assembly a transport-driven retrieval uses, so a live
    # result and a fixture produce an identically shaped set.
    retriever = scout_mod.ScoutRetriever(max_results=max_results, max_fetched=max_fetched,
                                         timeout_seconds=timeout_seconds)
    evidence = retriever._build_evidence(retrieval_request, brief, normalised, as_of=as_of)
    if rejected:
        evidence.notes.append(
            "%d retrieved item(s) were not accepted: %s"
            % (len(rejected), "; ".join(sorted({r["reason"] for r in rejected}))))

    # Conflicts are recorded **before** claims, because an unresolved conflict is one of
    # the conditions that refuses a claim. Recording them afterwards would let a claim
    # stand that the very same call then contradicts.
    refused_conflicts = _structured_conflicts(evidence, conflicts)

    # The evidence set is the authoritative output; claims are derived from it, only when
    # asked for, and only when the policy above permits one. The default is none.
    claims, refused_claims = _candidate_claims(evidence, proposals)

    return {
        "status": contract_mod.OK,
        "tier": decision.tier,
        "brief": brief.as_dict(),
        "accepted": len(normalised),
        "rejected": rejected,
        "evidence_set": evidence,
        "candidate_claims": claims,
        "claims_not_produced": refused_claims,
        "conflicts_not_recorded": refused_conflicts,
    }
