"""The scout boundary: handing an approved query out, and taking untrusted results back.

**Where the network actually is.** `bops-research-scout` is a Claude Code subagent whose
tool grant is `WebSearch, WebFetch` and nothing else. Those tools are invoked by the model
*inside* that subagent - Python cannot call them, and this package deliberately contains no
mechanism that could. That is not a limitation to work around; it is the whole architecture.
If Python could reach a web tool, the main process would hold file access and web access at
once, and ADR-0014's capability separation would be a comment rather than a control.

So this module implements the two Python-side halves of retrieval and nothing in between:

    ScoutBrief          what crosses out - the minimum, built only from an authorisation
    parse_reply         the production contract - BOPS-REC/1 lines bound to our operation
    parse_result        the internal envelope check `parse_reply` delegates to
    normalise_records   what comes back - validated, re-tiered locally, marked untrusted
    ScoutRetriever      the seam, driven by a caller-supplied transport

**The middle leg is not Python's.** A subagent is dispatched by the model through the
runtime's Task mechanism; there is no programmatic dispatch API a plugin's Python may call,
so `ScoutTransport` is a **test double** - it drives the production normalisation path from
fixtures - and never a production transport. In production the two halves are joined by an
orchestration surface written in markdown that the model reads: it serialises `ScoutBrief`,
dispatches `businessops:bops-research-scout`, and feeds the scout's **reply text** back to
`parse_reply`. See `commands/retrieval-slice.md`, ADR-0015 and ADR-0017.

**Two things the brief does not carry**, and neither is an oversight: the `ResearchRequest`
and the `AggregateDescriptor`s. A brief holds the approved text, the destination and an
operation id. There is no field for Business Context, dataset rows, descriptors, credentials
or the user's conversation, so the usual way internal data escapes - passing it "just for
context" - has nowhere to go.

**Two things the response cannot do.** It cannot declare its own source tier: tier is
assigned locally from the source identity by `sources.classify_tier`, because a page that
could name its own tier would name A. And it cannot ask for more: exactly one transport call
is made per retrieval, so text saying "search again for their revenue" is a string in an
evidence item, not a control-flow instruction.
"""

import datetime
import json

from . import contract as contract_mod
from . import evidence_set as evidence_mod
from . import retrieval as retrieval_mod
from . import sources as sources_mod

# -- bounds ------------------------------------------------------------------
#
# External input is unbounded by nature, so every quantity that could grow is capped. The
# figures are working defaults, documented rather than tuned: they are large enough for
# real research and small enough that a hostile or broken source cannot exhaust memory or
# fill a context window.

#: Search results accepted from one retrieval.
MAX_RESULTS = 20

#: Pages whose body may be fetched for one retrieval.
MAX_FETCHED = 8

#: Characters of retrieved content kept per item. Longer content is truncated and marked.
MAX_CONTENT_CHARS = 20000

#: Evidence items one set may hold from one retrieval.
MAX_EVIDENCE_ITEMS = 20

#: Characters in a query handed to the scout. A query longer than this is not a query.
MAX_QUERY_CHARS = 512

#: Seconds the caller's transport is expected to honour. Advisory: enforcement belongs to
#: the transport, since Python does not own the tool call.
DEFAULT_TIMEOUT_SECONDS = 60

#: The marking every retrieved item carries.
UNTRUSTED_EXTERNAL_DATA = "UNTRUSTED_EXTERNAL_DATA"

#: Fields a returned record may populate. Anything else is dropped rather than trusted -
#: a record that arrives with `system` or `disclosure_tier` set is a hostile page trying
#: to reach a control field, and the answer is that the field does not exist here.
ACCEPTED_RECORD_FIELDS = frozenset({
    "source", "reference", "url", "title", "publication_date", "retrieved_at",
    "source_type", "content", "snippet", "claim_kind",
})

# -- the production return contract: operation-bound line records -------------
#
# The scout is a model, not a library, so what comes back is whatever it wrote. From
# M9-C.15 the contract it writes to is **one self-identifying line per record** followed by
# one terminator, and `parse_reply` below is the only entry point a production retrieval
# uses. ADR-0017 records why, and supersedes the bare-envelope contract M9-C.1 hardened.
#
# The reason is evidence, not taste. Fourteen consecutive live replies violated the
# bare-envelope contract by wrapping a *correct* envelope in prose, and the whole reply -
# every record in it - was discarded each time. The line form asks the model for something
# it reliably does: a line at a time, with its prose left harmlessly around the lines. Eight
# of eight live trials complied (M9-C.13), and the complete gate-issued path was verified
# deterministically (M9-C.14).
#
# The operation id is what makes this safe rather than merely convenient. A line counts as a
# record only if it carries *this* retrieval's gate-bound operation, which a page author
# cannot know because it is minted per retrieval after the page was written. The declared
# count then closes the one remaining gap: a line copied verbatim out of a hostile page
# leaves the count disagreeing, and a disagreeing count fails the whole reply.

#: Prefix of one record line. Versioned like the envelope it replaced, for the same reason.
RECORD_TOKEN = "BOPS-REC/1"

#: Prefix of the single terminator line.
END_TOKEN = "BOPS-END/1"

#: Named so a caller can report which contract it parsed against.
SCOUT_REPLY_PROTOCOL = "bops.scout.lines/1"

# -- the canonical envelope --------------------------------------------------
#
# **Internal representation, not a wire contract.** `parse_reply` assembles one of these
# from the lines it accepted and hands it to `parse_result`, which is where the echo, status
# and record-list checks live and have always lived. Keeping that split means adoption moved
# the *shape the scout writes* without touching the validation beneath it.
#
# A scout cannot send one of these: a reply is text, and text is parsed as line protocol.
# `close_retrieval` still accepts an envelope **dict** so fixtures and `ScoutTransport` can
# drive the production path directly, which is a test seam, not a second scout contract.

#: The canonical envelope assembled internally from accepted record lines. Versioned, so a
#: change to the record vocabulary shows up at the boundary rather than three layers down.
SCOUT_RESULT_ENVELOPE = "bops.scout.result/1"

RESULT_OK = "ok"
RESULT_NO_SOURCE = "no_reliable_source_found"
RESULT_FAILED = "retrieval_failed"

RESULT_STATUSES = (RESULT_OK, RESULT_NO_SOURCE, RESULT_FAILED)

#: The only decoration tolerated around the JSON object. A model writing JSON very often
#: fences it, and rejecting that would be pedantry; tolerating *arbitrary* surrounding
#: prose would not be, because a retrieved page can contain a JSON object of its own and
#: the parse would then have a choice to make. It has none: fences and whitespace come
#: off, and what remains must be the whole object.
_FENCES = ("```json", "```JSON", "```")


class ScoutError(contract_mod.ResearchError):
    """The scout boundary was crossed incorrectly - a defect, not a user error."""


class ScoutBrief:
    """Everything the scout is given. Immutable, and built only from an authorisation.

    Constructible only from a `RetrievalRequest`, which is itself constructible only from a
    gate-issued authorisation. There is therefore no way to brief the scout on a query the
    gate did not approve, and no field in which anything internal could travel.
    """

    __slots__ = ("query_text", "destination", "operation", "max_results", "max_fetched",
                 "timeout_seconds", "_frozen")

    def __init__(self, request, max_results=MAX_RESULTS, max_fetched=MAX_FETCHED,
                 timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
        if type(request) is not retrieval_mod.RetrievalRequest:
            raise ScoutError(
                "a scout brief is built from a RetrievalRequest carrying a gate-issued "
                "authorisation; a query, a ResearchRequest or a dict cannot brief the "
                "scout")
        text = request.query_text or ""
        if not text.strip():
            raise ScoutError("an authorised query cannot be empty")
        if len(text) > MAX_QUERY_CHARS:
            raise ScoutError(
                "the authorised query is %d characters, above the %d-character bound; a "
                "query that long is not a query" % (len(text), MAX_QUERY_CHARS))

        self.query_text = text
        self.destination = request.destination.identity()
        self.operation = request.operation
        self.max_results = max(1, min(int(max_results), MAX_RESULTS))
        self.max_fetched = max(0, min(int(max_fetched), MAX_FETCHED))
        self.timeout_seconds = int(timeout_seconds)
        self._frozen = True

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise ScoutError("a scout brief is immutable once built; %r cannot be changed"
                             % name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise ScoutError("a scout brief is immutable once built")

    def as_dict(self):
        """Exactly what crosses the boundary. Audit this and you have seen everything."""
        return {"query_text": self.query_text, "destination": self.destination,
                "operation": self.operation, "max_results": self.max_results,
                "max_fetched": self.max_fetched,
                "timeout_seconds": self.timeout_seconds}

    def __repr__(self):
        return "ScoutBrief(%r, %s)" % (self.query_text[:48], self.destination)


def _clean(value, limit=None):
    if value is None:
        return None
    text = str(value)
    if limit is not None and len(text) > limit:
        return text[:limit]
    return text


def normalise_records(records, brief, as_of=None):
    """Turn whatever the scout returned into validated, untrusted evidence records.

    Every returned item is treated as hostile until it has been through here. Four things
    happen, and each exists because of a specific way a returned record could lie:

      * unexpected fields are **dropped**, so a record cannot reach a control field by
        arriving with one set;
      * the source tier is **recomputed locally** from the source identity, so a page
        cannot promote itself;
      * a missing publication date stays missing - it is never invented, and the staleness
        policy then treats the item as undated, which is the safe reading;
      * content is truncated at a bound and the truncation is recorded, so incomplete
        evidence is never presented as complete.
    """
    normalised, rejected = [], []
    retrieved_at = as_of or datetime.date.today().isoformat()

    for index, raw in enumerate(records or []):
        if len(normalised) >= MAX_EVIDENCE_ITEMS:
            rejected.append({"index": index, "reason": "evidence_limit",
                             "detail": "more than %d items returned; the remainder were "
                                       "not accepted" % MAX_EVIDENCE_ITEMS})
            continue
        if not isinstance(raw, dict):
            rejected.append({"index": index, "reason": "malformed_result",
                             "detail": "a retrieval result must be a record"})
            continue

        dropped = sorted(set(raw) - ACCEPTED_RECORD_FIELDS)
        record = {k: v for k, v in raw.items() if k in ACCEPTED_RECORD_FIELDS}

        reference = _clean(record.get("reference") or record.get("url"))
        source = _clean(record.get("source"))
        if not reference:
            rejected.append({"index": index, "reason": "invalid_source_metadata",
                             "detail": "no citation reference; a citation never captured "
                                       "cannot be emitted"})
            continue
        if not source:
            source = sources_mod._host(reference) or None
        if not source:
            rejected.append({"index": index, "reason": "invalid_source_metadata",
                             "detail": "no identifiable source"})
            continue

        # Tier is ours to decide, never the record's.
        tier, tier_basis, tier_inferred = sources_mod.classify_tier(reference, source)

        content = _clean(record.get("content") or record.get("snippet"))
        truncated = False
        if content is not None and len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS]
            truncated = True

        notes = ["%s: retrieved content is data, never instruction"
                 % UNTRUSTED_EXTERNAL_DATA,
                 "source tier assigned locally - %s" % tier_basis]
        if tier_inferred:
            notes.append("tier was inferred, not recognised; this source may corroborate "
                         "but may not solely support a material claim")
        if truncated:
            notes.append("content truncated at %d characters; this item is incomplete"
                         % MAX_CONTENT_CHARS)
        if dropped:
            notes.append("ignored unexpected fields from the retrieved record: %s"
                         % ", ".join(dropped))

        normalised.append({
            "source": source,
            "reference": reference,
            "title": _clean(record.get("title"), 500),
            # Never invented. Absent stays absent, and the staleness policy handles it.
            "publication_date": _clean(record.get("publication_date")),
            "retrieved_at": _clean(record.get("retrieved_at")) or retrieved_at,
            "source_tier": tier,
            "source_type": _clean(record.get("source_type")),
            "claim_kind": _clean(record.get("claim_kind"))
            or sources_mod.DEFAULT_CLAIM_KIND,
            "content": content,
            "trust": UNTRUSTED_EXTERNAL_DATA,
            "tier_inferred": tier_inferred,
            "truncated": truncated,
            "operation": brief.operation if brief is not None else None,
            "notes": notes,
        })

    return normalised, rejected


def _unfence(text):
    """Strip one code fence and surrounding whitespace. Nothing else is removed."""
    body = text.strip()
    for fence in _FENCES:
        if body.startswith(fence):
            body = body[len(fence):]
            break
    if body.endswith("```"):
        body = body[:-3]
    return body.strip()


#: Why a reply was refused. Structural problems only - these never describe a *research*
#: outcome, which is what `status` in the assembled envelope is for.
NO_TERMINATOR = "no_terminator"
COUNT_MISMATCH = "count_mismatch"
MALFORMED_RECORD = "malformed_record"


def render_reply(operation, records):
    """Produce the line form. Used to build deterministic fixtures, never in production."""
    lines = ["%s %s %s" % (RECORD_TOKEN, operation, json.dumps(r, sort_keys=True))
             for r in records]
    lines.append("%s %s %d" % (END_TOKEN, operation, len(records)))
    return "\n".join(lines)


def parse_reply(reply, brief):
    """Parse what the scout actually returned. Returns `(records, failure)`.

    **This is the production scout contract** (ADR-0017). The reply is text: zero or more

        BOPS-REC/1 <operation> {one-line JSON object}

    lines, then exactly one

        BOPS-END/1 <operation> <count>

    Ordinary prose may sit anywhere around those lines and is read as content, never as
    instruction and never as a record. That tolerance is the point of the shape, and it costs
    nothing, because a line is a record only if it carries this retrieval's operation id.

    Four structural checks, each a way the boundary could be crossed rather than a matter of
    tidiness:

      * **the operation** on every line must be the brief's, character for character, so a
        line minted for another retrieval - or copied out of a page - is not a record here;
      * **exactly one terminator**, because two terminators are two replies and neither can
        be shown to be ours;
      * **the declared count must equal the number of record lines**, which is what a
        verbatim-smuggled line cannot satisfy: it inflates the line count the scout already
        committed to, and the whole reply fails;
      * **each record is one bare single-line JSON object**, so a multi-line or truncated
        record is refused rather than half-read.

    Nothing is repaired and no line is rescued: a structural problem yields no records at
    all, exactly as the envelope parser has always behaved on a malformed payload. Never
    raises - a scout that answered badly is a research outcome, not a crash.

    A reply whose terminator declares `0` with no record lines is **not** a structural
    problem. It is a successful retrieval that found nothing citable, so it assembles an
    envelope carrying `RESULT_NO_SOURCE` and reaches the caller as insufficient evidence
    with nothing fabricated (M9-C.14).
    """
    if isinstance(reply, bytes):
        try:
            reply = reply.decode("utf-8")
        except UnicodeDecodeError:
            reply = None
    if not isinstance(reply, str):
        return [], _structural_failure(
            MALFORMED_RECORD,
            "The research scout returned %s where a %s reply was expected."
            % (type(reply).__name__, SCOUT_REPLY_PROTOCOL))

    operation = str(brief.operation) if brief is not None else ""
    record_prefix = "%s %s " % (RECORD_TOKEN, operation)
    end_prefix = "%s %s " % (END_TOKEN, operation)

    records, declared = [], None
    for line in reply.splitlines():
        line = line.strip()
        if line.startswith(record_prefix):
            body = line[len(record_prefix):].strip()
            try:
                parsed = json.loads(body)
            except ValueError:
                return [], _structural_failure(
                    MALFORMED_RECORD,
                    "A %s line did not carry one bare JSON object, so the reply was not "
                    "read." % RECORD_TOKEN)
            if not isinstance(parsed, dict):
                return [], _structural_failure(
                    MALFORMED_RECORD,
                    "A %s line carried %s where a record object was expected."
                    % (RECORD_TOKEN, type(parsed).__name__))
            records.append(parsed)
        elif line.startswith(end_prefix):
            if declared is not None:
                return [], _structural_failure(
                    COUNT_MISMATCH,
                    "The reply carries more than one %s line, so it is not one reply."
                    % END_TOKEN)
            try:
                declared = int(line[len(end_prefix):].strip())
            except ValueError:
                return [], _structural_failure(
                    MALFORMED_RECORD,
                    "The %s line did not declare an integer count." % END_TOKEN)

    if declared is None:
        return [], _structural_failure(
            NO_TERMINATOR,
            "The research scout's reply carries no %s line for this retrieval, so nothing "
            "in it is attributable and nothing was read." % END_TOKEN)
    if declared != len(records):
        return [], _structural_failure(
            COUNT_MISMATCH,
            "The reply declares %d record(s) and carries %d, so the whole reply was "
            "discarded rather than part of it accepted." % (declared, len(records)))

    # Assembled from the brief, never from the reply: the scout supplies records and nothing
    # else, which is the same division `parse_result` already enforces. The status is the one
    # production already defines for an empty result.
    envelope = {
        "envelope": SCOUT_RESULT_ENVELOPE,
        "operation": operation,
        "query_text": brief.query_text if brief is not None else None,
        "status": RESULT_OK if records else RESULT_NO_SOURCE,
        "records": records,
    }
    return parse_result(envelope, brief)


def _structural_failure(reason, explanation):
    """A refused reply. `UNAVAILABLE` because a malformed reply is a defect, not an answer."""
    return contract_mod.failure(
        contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE, explanation,
        protocol=SCOUT_REPLY_PROTOCOL, structural_problem=reason)


def parse_result(payload, brief):
    """Validate the canonical envelope. Returns `(records, failure)`.

    **Internal validator, not the scout contract.** `parse_reply` assembles an envelope from
    the lines the scout actually sent and calls this; fixtures and `ScoutTransport` may also
    build one directly. No scout reply reaches here without going through `parse_reply`
    first, which is what keeps one production contract rather than two (ADR-0017).

    Never raises: a scout that answered badly is a research outcome, not a crash, and a
    traceback is not an answer to a research question.

    Four things are checked before any record is read, and each is a way the boundary could
    be crossed rather than a matter of tidiness:

      * the **envelope name** must match, so an arbitrary JSON object - including one a
        retrieved page contained - is not mistaken for a scout result;
      * the **operation** must echo the brief's, so a result cannot be attributed to a
        retrieval it did not come from;
      * the **query text** must echo the brief's, which is where "the query is fixed"
        stops being an instruction the scout is asked to honour and becomes a property
        checked on the way back;
      * the **status** is read before the records, so "no reliable source found" arrives as
        a structured research failure instead of an empty list that reads like a bug.
    """
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            payload = None
    if isinstance(payload, str):
        try:
            payload = json.loads(_unfence(payload))
        except (ValueError, TypeError):
            return [], contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                "The research scout did not return a parsable %s envelope, so nothing "
                "could be cited." % SCOUT_RESULT_ENVELOPE)

    if not isinstance(payload, dict):
        return [], contract_mod.failure(
            contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
            "The research scout returned %s where a %s envelope was expected."
            % (type(payload).__name__, SCOUT_RESULT_ENVELOPE))

    if payload.get("envelope") != SCOUT_RESULT_ENVELOPE:
        return [], contract_mod.failure(
            contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
            "The returned object is not a %s envelope; it is not treated as retrieval "
            "output." % SCOUT_RESULT_ENVELOPE,
            envelope=_clean(payload.get("envelope"), 80))

    if brief is not None:
        operation = payload.get("operation")
        if operation is not None and str(operation) != str(brief.operation):
            return [], contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_INVALID_PROVENANCE,
                "The returned envelope names a different retrieval operation than the one "
                "briefed, so it cannot be attributed to this request.")
        returned_query = payload.get("query_text")
        if returned_query is not None and str(returned_query) != brief.query_text:
            return [], contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_INVALID_PROVENANCE,
                "The returned envelope echoes a different query than the one the gate "
                "approved. The query is fixed; a result for a substituted query is "
                "discarded.")

    status = payload.get("status", RESULT_OK)
    if status not in RESULT_STATUSES:
        return [], contract_mod.failure(
            contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
            "The research scout reported an unrecognised status.",
            reported_status=_clean(status, 60))
    if status == RESULT_NO_SOURCE:
        return [], contract_mod.failure(
            contract_mod.INSUFFICIENT_EVIDENCE, contract_mod.REASON_NO_ADEQUATE_SOURCE,
            "No reliable source found. The scout searched and reported nothing that met "
            "the source bar.")
    if status == RESULT_FAILED:
        return [], contract_mod.failure(
            contract_mod.UNAVAILABLE, contract_mod.REASON_SOURCE_UNAVAILABLE,
            "External retrieval failed or was blocked; no evidence was returned.")

    records = payload.get("records")
    if not isinstance(records, list):
        return [], contract_mod.failure(
            contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
            "The envelope reported success but carries no record list.")
    return records, None


class ScoutTransport:
    """How a brief reaches the scout and a response comes back.

    Injected rather than imported. In production the caller supplies a transport that
    dispatches the `bops-research-scout` subagent - which is where `WebSearch` and
    `WebFetch` actually run - and returns the records it reported. In tests the caller
    supplies a fixture. Both drive identical code here, which is the point: the adversarial
    fixtures exercise the same normalisation a live page will meet.
    """

    name = "abstract"
    available = False

    def dispatch(self, brief):                        # pragma: no cover - abstract
        raise NotImplementedError(
            "a ScoutTransport subclass implements dispatch(brief) -> [record, ...]")


class UnavailableTransport(ScoutTransport):
    """The default. No scout is wired up, so retrieval reports that honestly."""

    name = "unavailable"
    available = False

    def dispatch(self, brief):
        raise ScoutError("no scout transport is configured")


class RecordingTransport(ScoutTransport):
    """A deterministic transport for tests: returns fixed records, records every call.

    Takes the production path exactly, so a hostile fixture is handled by the same
    normalisation as a hostile page. `calls` is what proves one-shot behaviour and
    ordering.
    """

    name = "recording"

    def __init__(self, records=(), failure=None):
        self.records = list(records)
        self.failure = failure
        self.available = True
        self.calls = []

    def dispatch(self, brief):
        self.calls.append(brief.as_dict())
        if self.failure is not None:
            raise self.failure
        return list(self.records)


class ScoutRetriever(retrieval_mod.Retriever):
    """Retrieval through the scout. The only retriever that reaches the outside world.

    Inherits the M9-A boundary unchanged - `retrieve()` still refuses anything but a
    `RetrievalRequest` carrying a gate-issued, unaltered, authorised decision - and adds
    the brief, the transport call and normalisation.

    Exactly **one** transport call is made per retrieval. Nothing in a returned record can
    cause a second: the loop that would do it does not exist.
    """

    name = "scout"

    def __init__(self, transport=None, max_results=MAX_RESULTS, max_fetched=MAX_FETCHED,
                 timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
        self.transport = transport or UnavailableTransport()
        self.max_results = max_results
        self.max_fetched = max_fetched
        self.timeout_seconds = timeout_seconds
        self.available = bool(getattr(self.transport, "available", False))
        #: Every brief this retriever handed out, for audit and for tests.
        self.briefs = []
        self.rejected = []

    def brief_for(self, request):
        """The brief that would be sent. Built from the authorisation, nothing else."""
        return ScoutBrief(request, max_results=self.max_results,
                          max_fetched=self.max_fetched,
                          timeout_seconds=self.timeout_seconds)

    def retrieve(self, request, as_of=None):
        """Authorised retrieval. Returns an `EvidenceSet` or a `ResearchFailure`."""
        # The M9-A boundary runs first and unchanged: type, gate issuance, refusal,
        # binding and authorisation. Only then does a brief exist.
        if type(request) is not retrieval_mod.RetrievalRequest:
            raise retrieval_mod.RetrievalError(
                "retrieve() accepts only a RetrievalRequest built from an authorised "
                "disclosure decision")
        from . import gate as gate_mod
        if not gate_mod.is_gate_issued(request.decision):
            raise retrieval_mod.RetrievalError(
                "the authorisation behind this request was not issued by the disclosure "
                "gate")
        if not request.decision.authorised or not request.decision.binding_intact:
            raise retrieval_mod.RetrievalError(
                "the authorisation behind this request is no longer valid; retrieval "
                "must not run")

        if not self.available:
            return contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                "No research scout transport is configured, so no external retrieval can "
                "run. The disclosure boundary is intact; there is simply nothing on the "
                "other side of it.", retriever=self.name)

        brief = self.brief_for(request)
        self.briefs.append(brief)

        try:
            records = self.transport.dispatch(brief)
        except TimeoutError as exc:
            return contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                "External retrieval timed out after %ss; no evidence was returned."
                % brief.timeout_seconds, detail=str(exc))
        except ScoutError as exc:
            return contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                "The research scout could not run: %s" % exc)
        except Exception as exc:                      # a transport is foreign code
            # Never a traceback as a research answer.
            return contract_mod.failure(
                contract_mod.UNAVAILABLE, contract_mod.REASON_SOURCE_UNAVAILABLE,
                "External retrieval failed: %s" % type(exc).__name__,
                detail=str(exc)[:200])

        normalised, rejected = normalise_records(records, brief, as_of=as_of)
        self.rejected.extend(rejected)

        if not normalised:
            return contract_mod.failure(
                contract_mod.INSUFFICIENT_EVIDENCE,
                contract_mod.REASON_NO_ADEQUATE_SOURCE,
                "Retrieval returned nothing that could be cited. No reliable source found.",
                rejected=rejected)

        evidence = self._build_evidence(request, brief, normalised, as_of=as_of)
        if rejected:
            evidence.notes.append(
                "%d retrieved item(s) were not accepted: %s"
                % (len(rejected), "; ".join(sorted({r["reason"] for r in rejected}))))
        return evidence

    def _build_evidence(self, request, brief, normalised, as_of=None):
        evidence = evidence_mod.EvidenceSet(
            operation=request.operation, subject=request.subject,
            category=request.category, query_text=request.query_text,
            destination=request.destination.as_dict(), disclosure_tier=request.tier)
        for record in normalised:
            evidence.add(evidence_mod.EvidenceItem(
                source=record["source"], reference=record["reference"],
                source_tier=record["source_tier"], retrieved_at=record["retrieved_at"],
                title=record["title"], publication_date=record["publication_date"],
                source_type=record["source_type"], content=record["content"],
                claim_kind=record["claim_kind"], operation=record["operation"],
                notes=record["notes"], as_of=as_of or record["retrieved_at"]))
        return evidence


def candidate_claim(item, statement, material=True):
    """A class-3 claim from one evidence item - or a refusal explaining why not.

    Mechanical only: it copies provenance from the item onto a `Claim` and refuses where
    policy forbids one. It does **not** read the content, decide what the source says, or
    interpret anything - that is the analysis layer, and it is not part of M9-B.

    Returns `(claim, None)` or `(None, ResearchFailure)`.
    """
    from .. import evidence as ledger_mod

    if not item.usable:
        return None, contract_mod.failure(
            contract_mod.INSUFFICIENT_EVIDENCE, contract_mod.REASON_NO_ADEQUATE_SOURCE,
            "Tier D sources are excluded and cannot support a claim.",
            source=item.source)
    if material and not item.may_stand_alone:
        return None, contract_mod.failure(
            contract_mod.INSUFFICIENT_EVIDENCE, contract_mod.REASON_NO_ADEQUATE_SOURCE,
            "Tier C corroborates but is never the sole support for a material claim; "
            "corroborate it with a tier A or B source.", source=item.source)
    if not item.publication_date:
        return None, contract_mod.failure(
            contract_mod.INSUFFICIENT_EVIDENCE, contract_mod.REASON_INVALID_PROVENANCE,
            "The source carries no publication date, so a class-3 claim cannot record "
            "one. A date is not inferred.", source=item.source)

    claim = ledger_mod.Claim(
        statement, ledger_mod.EXTERNAL_SOURCED,
        source=item.source, citation=item.reference,
        source_date=item.publication_date, source_tier=item.source_tier,
        caveats=([item.freshness["statement"]] if item.stale else []))
    return claim, None
