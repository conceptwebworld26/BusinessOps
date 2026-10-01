"""Routing for `/ask-business-data`: a question in, a *pointer to existing work* out.

This module answers nothing itself. It decides **which already-computed thing** a question
is about — a KPI from the Milestone 5 catalogue, or a dimension and intent the Milestone 6
analytics already produce — and then reads that result. There is no arithmetic here and no
path by which a question produces a number that the deterministic engine did not produce.

The concept vocabulary is derived from metadata the repository already holds: KPI names and
identifiers come from the catalogue, dimension names from the semantic roles. Only the
*intent* words ("largest", "grew", "concentration") are declared here, because nothing else
in the system needs to know how a person phrases a question.

Four outcomes, and they are not interchangeable:

    routed                the question maps to exactly one concept
    clarification_needed  several concepts fit equally, or none was recognised
    unsupported           the question asks for something another command owns
    unavailable           the concept was found but the engine could not produce it

Guessing is never an outcome. A question that maps to nothing produces a request for
clarification listing what *can* be answered, not a plausible answer.
"""

import re

from ..analytics import contract as analytics_contract
from ..analytics import domain as analytics_domain
from ..kpi import contract as kpi_contract
from ..kpi import registry as kpi_registry

# -- outcomes ---------------------------------------------------------------

ROUTED = "routed"
CLARIFICATION_NEEDED = "clarification_needed"
UNSUPPORTED = "unsupported"
UNAVAILABLE = "unavailable"
ANSWERED = "answered"

# -- concept kinds ----------------------------------------------------------

KPI = "kpi"
DIMENSION = "dimension"

#: Words that carry no routing signal. Deliberately short: an aggressive stop list starts
#: discarding business vocabulary.
STOP_WORDS = frozenset("""
a an and are as at be been by can did do does for from had has have how i in into is it
me most my of on or our ours she he they them their the this that these those to was we
were what when where which who whom why will with you your
""".split())

#: Intent → the words that signal it. Routing vocabulary only; no business rule lives here.
INTENTS = (
    ("largest", ("largest", "highest", "biggest", "best", "top", "leading", "greatest")),
    ("movement", ("grew", "grow", "growth", "growing", "increase", "increased",
                  "increasing", "decline", "declined", "declining", "fell", "fall",
                  "falling", "drop", "dropped", "shrank", "moved", "movement", "change",
                  "changed", "fastest", "slowest", "worst")),
    ("mix", ("mix", "composition", "proportion")),
    ("contribution", ("contribute", "contributed", "contributes", "contribution",
                      "drove", "driver", "drivers")),
    ("concentration", ("concentration", "concentrated", "reliant", "dependent",
                       "dependence", "exposure", "exposed")),
    ("repeat", ("repeat", "repeated", "returning", "again", "twice")),
    ("cohorts", ("cohort", "cohorts")),
)

#: Phrases that ask for a sub-period. BusinessOps computes over the whole supplied range at
#: monthly granularity, so these are answered with an explicit note rather than silently
#: treated as if the whole range had been asked for.
PERIOD_QUALIFIERS = (
    "last quarter", "this quarter", "last month", "this month", "last year",
    "this year", "year to date", "ytd", "last week", "this week", "q1", "q2", "q3", "q4",
)


INTENT_PHRASES = (
    ("repeat", ("more than once", "multiple times", "come back", "came back")),
    ("concentration", ("how much of our revenue", "share of total")),
    ("largest", ("the most",)),
)

#: Which analytical domain owns a dimension once an intent is known.
DIMENSION_DOMAIN = {
    "customer": "customer",
    "product": "product",
    "category": "product",
    "region": "sales",
    "salesperson": "sales",
}

#: Capabilities another BusinessOps command owns. This router answers only from metrics and
#: analyses already computed on the supplied file, so these are recognised precisely: the
#: refusal names what was asked for and the command that does it, rather than saying
#: "not understood".
OUT_OF_SCOPE = (
    ("forecasting", "/revenue-forecast",
     ("forecast", "forecasts", "forecasting", "predict", "predicted", "prediction",
      "predictions", "projection", "projections", "projected", "extrapolate"),
     ("next quarter", "next year", "next month", "will we", "going to be",
      "how much will")),
    ("anomaly detection", "/anomaly-detection",
     ("anomaly", "anomalies", "anomalous", "outlier", "outliers", "fraud", "fraudulent",
      "suspicious"),
     ()),
    ("external research",
     "/company-analysis, /market-analysis, /competitor-analysis, /industry-research or "
     "/benchmark-comparison",
     ("competitor", "competitors", "competition", "industry", "benchmark", "benchmarks",
      "benchmarked", "peers", "market"),
     ("compared to the market", "industry average")),
)


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP_WORDS]


class Routing:
    """Where one question was sent, and why."""

    __slots__ = ("question", "status", "concept_kind", "concept_id", "concept_label",
                 "dimension", "intent", "domain", "candidates", "reason", "score",
                 "period_qualifier")

    def __init__(self, question, status, concept_kind=None, concept_id=None,
                 concept_label=None, dimension=None, intent=None, domain=None,
                 candidates=(), reason=None, score=None, period_qualifier=None):
        self.question = question
        self.status = status
        self.concept_kind = concept_kind
        self.concept_id = concept_id
        self.concept_label = concept_label
        self.dimension = dimension
        self.intent = intent
        self.domain = domain
        self.candidates = list(candidates)
        self.reason = reason
        self.score = score
        self.period_qualifier = period_qualifier

    @property
    def routed(self):
        return self.status == ROUTED

    def as_dict(self):
        record = {"question": self.question, "status": self.status,
                  "concept_kind": self.concept_kind, "concept_id": self.concept_id,
                  "concept_label": self.concept_label, "dimension": self.dimension,
                  "intent": self.intent, "domain": self.domain,
                  "candidates": list(self.candidates), "reason": self.reason,
                  "period_qualifier": self.period_qualifier,
                  "score": (str(self.score) if self.score is not None else None)}
        return {k: v for k, v in record.items() if v not in (None, [])}

    def __repr__(self):
        return "Routing(%s: %s %s)" % (self.status, self.concept_kind or "-",
                                       self.concept_id or "")


# ---------------------------------------------------------------------------
# Vocabulary, derived from what the repository already declares
# ---------------------------------------------------------------------------

def kpi_vocabulary():
    """`{kpi_id: (label, keyword set)}` built from the Milestone 5 catalogue.

    Keywords come from each metric's own name and identifier. Nothing is invented here, so
    a metric added to the catalogue becomes askable without touching this module.
    """
    vocabulary = {}
    for definition in kpi_registry.definitions():
        words = set(_tokens(definition.name)) | set(_tokens(definition.kpi_id))
        # An abbreviation in brackets — "(DSO)", "(NRR)" — is how people actually ask.
        words |= {w for w in re.findall(r"\(([A-Z]{2,5})\)", definition.name)}
        vocabulary[definition.kpi_id] = (definition.name,
                                         {w.lower() for w in words if w})
    return vocabulary


def dimension_vocabulary():
    """`{dimension: keyword set}` from the semantic roles the analytics layer segments by."""
    vocabulary = {}
    for role, name in analytics_domain.DIMENSIONS:
        words = {name, name + "s", role}
        if name.endswith("y"):
            words.add(name[:-1] + "ies")
        vocabulary[name] = {w.lower() for w in words}
    return vocabulary


def _detect_intent(question):
    lowered = (question or "").lower()
    tokens = set(_tokens(question))
    for intent, phrases in INTENT_PHRASES:
        if any(phrase in lowered for phrase in phrases):
            return intent
    for intent, words in INTENTS:
        if tokens & set(words):
            return intent
    return None


def _detect_period_qualifier(question):
    lowered = (question or "").lower()
    for phrase in PERIOD_QUALIFIERS:
        if re.search(r"\b%s\b" % re.escape(phrase), lowered):
            return phrase
    return None


def _detect_out_of_scope(question):
    lowered = (question or "").lower()
    tokens = set(_tokens(question))
    for capability, owner, words, phrases in OUT_OF_SCOPE:
        if tokens & set(words) or any(phrase in lowered for phrase in phrases):
            return capability, owner
    return None, None


def _score_kpis(tokens, vocabulary):
    """Rank metrics by how much of their own name the question uses."""
    scored = []
    asked = set(tokens)
    for kpi_id, (label, words) in vocabulary.items():
        overlap = asked & words
        if not overlap:
            continue
        # Coverage of the metric's own vocabulary, so "revenue" beats "revenue growth"
        # for the bare question and loses to it when "growth" is also asked.
        scored.append((len(overlap) / float(len(words)), len(overlap), kpi_id, label))
    scored.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return scored


def route(question):
    """Decide what a question is about. Pure: no data is consulted."""
    if not question or not question.strip():
        return Routing(question, CLARIFICATION_NEEDED,
                       reason="No question was supplied. Ask about a metric (for example "
                              "'what was gross margin?') or a dimension (for example "
                              "'which region grew fastest?').")

    capability, owner = _detect_out_of_scope(question)
    if capability:
        return Routing(question, UNSUPPORTED,
                       reason="This question asks for %s, which this command does not "
                              "answer: it reads only metrics already computed on the "
                              "supplied file. Use %s. Nothing was estimated in its place."
                              % (capability, owner))

    tokens = _tokens(question)
    intent = _detect_intent(question)
    qualifier = _detect_period_qualifier(question)

    dimensions = dimension_vocabulary()
    asked = set(tokens)
    matched_dimensions = sorted(name for name, words in dimensions.items()
                                if asked & words)

    scored = _score_kpis(tokens, kpi_vocabulary())

    # A dimension plus an intent is a question about a ranking or a movement, which the
    # analytics layer answers; a dimension alone is not yet a question.
    if matched_dimensions and intent:
        if len(matched_dimensions) > 1:
            return Routing(question, CLARIFICATION_NEEDED,
                           intent=intent, candidates=matched_dimensions,
                           reason="The question mentions more than one dimension (%s). "
                                  "Ask about one at a time."
                                  % ", ".join(matched_dimensions))
        dimension = matched_dimensions[0]
        return Routing(question, ROUTED, concept_kind=DIMENSION, concept_id=dimension,
                       concept_label=dimension, dimension=dimension, intent=intent,
                       domain=DIMENSION_DOMAIN.get(dimension, "sales"),
                       period_qualifier=qualifier)

    if scored:
        best = scored[0]
        rivals = [row for row in scored[1:] if row[0] == best[0] and row[1] == best[1]]
        if rivals:
            candidates = [best[2]] + [row[2] for row in rivals]
            return Routing(question, CLARIFICATION_NEEDED, candidates=sorted(candidates),
                           reason="More than one metric fits equally well (%s). Name the "
                                  "one you mean." % ", ".join(sorted(candidates)))
        return Routing(question, ROUTED, concept_kind=KPI, concept_id=best[2],
                       concept_label=best[3], intent=intent, domain="financial",
                       score=round(best[0], 3), period_qualifier=qualifier)

    if matched_dimensions:
        return Routing(question, CLARIFICATION_NEEDED,
                       candidates=matched_dimensions,
                       reason="The question names %s but not what to report about it. Ask "
                              "for the largest, the movement, the mix, the contribution or "
                              "the concentration."
                              % ", ".join(matched_dimensions))

    return Routing(question, CLARIFICATION_NEEDED,
                   candidates=sorted(dimension_vocabulary()),
                   reason="No metric or dimension in this dataset matched the question. "
                          "BusinessOps can answer about any metric in the KPI catalogue, or "
                          "about a dimension (%s) combined with largest, movement, mix, "
                          "contribution or concentration."
                          % ", ".join(sorted(dimension_vocabulary())))


# ---------------------------------------------------------------------------
# Resolution — reading the answer out of results that already exist
# ---------------------------------------------------------------------------

#: Which finding identifier fragment each intent corresponds to.
INTENT_FRAGMENT = {
    "largest": "largest",
    "movement": ".movement.",
    "mix": ".mix.",
    "contribution": "contribution",
    "concentration": "concentration",
    "repeat": "customers.repeat",
    "cohorts": "customers.cohorts",
}


class Answer:
    """What the question resolved to, or why it did not."""

    __slots__ = ("routing", "status", "statement", "finding", "kpi", "reason",
                 "supporting", "caveats")

    def __init__(self, routing, status, statement=None, finding=None, kpi=None,
                 reason=None, supporting=(), caveats=()):
        self.routing = routing
        self.status = status
        self.statement = statement
        self.finding = finding
        self.kpi = kpi
        self.reason = reason
        self.supporting = list(supporting)
        self.caveats = list(caveats)

    @property
    def answered(self):
        return self.status == ANSWERED

    def as_dict(self):
        record = {"status": self.status, "statement": self.statement,
                  "reason": self.reason, "routing": self.routing.as_dict()}
        if self.finding is not None:
            record["finding"] = self.finding.as_dict()
        if self.kpi is not None:
            record["kpi"] = self.kpi.as_dict()
        if self.supporting:
            record["supporting"] = [f.as_dict() for f in self.supporting]
        if self.caveats:
            record["caveats"] = list(self.caveats)
        return record

    def __repr__(self):
        return "Answer(%s)" % self.status


def _wants_decrease(question):
    lowered = (question or "").lower()
    return any(word in lowered for word in
               ("declin", "fell", "fall", "drop", "shrank", "worst", "slowest", "lost"))


def _rendered(result):
    """The metric value as a sentence reads it. Rounding happens once, here."""
    if result.unit == kpi_contract.CURRENCY:
        return analytics_domain.text_amount(result.value, result.currency)
    if result.unit == kpi_contract.PERCENT:
        return analytics_domain.text_percent(result.value)
    if result.unit == kpi_contract.DAYS:
        return "%s days" % analytics_domain.text_amount(result.value)
    return analytics_domain.text_amount(result.value)


def _period_caveats(routing, periods):
    """A sub-period question is answered over the whole range, and says so.

    Silently returning the full-period figure for "last quarter" would answer a different
    question from the one asked, which is the specific failure this layer exists to avoid.
    """
    if not routing.period_qualifier:
        return []
    covered = ("%s to %s" % (periods[0], periods[-1])) if periods else "the supplied range"
    return ["The question asks about %r, but BusinessOps computes over the whole reporting "
            "period (%s) and does not filter to a sub-period, so this figure covers the "
            "full range." % (routing.period_qualifier, covered)]


def resolve(routing, kpis, analyses, semantic_map=None, periods=()):
    """Read the answer out of results the engine already produced.

    Never computes. If the concept exists but the engine could not produce it, the engine's
    own reason is returned verbatim — including for the question "why is X unavailable?",
    which is the same lookup.
    """
    if routing.status != ROUTED:
        return Answer(routing, routing.status, reason=routing.reason)

    if routing.concept_kind == KPI:
        result = (kpis or {}).get(routing.concept_id)
        if result is None:
            return Answer(routing, UNAVAILABLE,
                          reason="%s is in the catalogue but was not computed in this run."
                                 % routing.concept_label)
        if not result.available:
            return Answer(routing, UNAVAILABLE, kpi=result,
                          reason=result.reason
                                 or "The engine could not produce %s." % result.label)
        return Answer(routing, ANSWERED, kpi=result,
                      statement="%s is %s." % (result.label, _rendered(result)),
                      caveats=_period_caveats(routing, periods))

    # A dimension question needs the column to exist before anything else.
    if semantic_map is not None:
        role = {name: role for role, name in analytics_domain.DIMENSIONS}.get(
            routing.dimension)
        if role and not semantic_map.column_for(role):
            return Answer(routing, UNAVAILABLE,
                          reason="No column in this dataset is mapped to %s, so the "
                                 "question cannot be answered from it." % role)

    analysis = (analyses or {}).get(routing.domain)
    if analysis is None:
        return Answer(routing, UNAVAILABLE,
                      reason="The %s analysis was not run for this question."
                             % routing.domain)
    if analysis.status != analytics_contract.AVAILABLE:
        return Answer(routing, UNAVAILABLE,
                      reason=analysis.reason
                             or "The %s analysis is %s." % (routing.domain,
                                                            analysis.status))

    fragment = INTENT_FRAGMENT.get(routing.intent)
    matches = [f for f in analysis.findings
               if (fragment or "") in f.analysis_id
               and (routing.intent in ("repeat", "cohorts")
                    or f.dimension == routing.dimension)]
    if not matches:
        blocked = [item for item in analysis.limitations
                   if item.subject == routing.dimension]
        if blocked:
            return Answer(routing, UNAVAILABLE, reason=blocked[0].reason)
        return Answer(routing, UNAVAILABLE,
                      reason="The %s analysis produced nothing about %s %s."
                             % (routing.domain, routing.dimension, routing.intent))

    if routing.intent == "movement":
        wants_decrease = _wants_decrease(routing.question)
        ordered = sorted(matches, key=lambda f: (f.change, f.analysis_id))
        chosen = ordered[0] if wants_decrease else ordered[-1]
    else:
        chosen = matches[0]

    return Answer(routing, ANSWERED, finding=chosen, statement=chosen.statement,
                  supporting=_supporting(analysis, routing, matches, chosen),
                  caveats=_period_caveats(routing, analysis.periods))


def _supporting(analysis, routing, matches, chosen):
    """The other readings of the same question, so a near-miss is visible not hidden.

    "Which product contributed most to revenue?" can mean the largest line or the largest
    driver of the change. The router picks one; this returns the other rather than leaving
    the reader to wonder whether it was considered.
    """
    supporting = [f for f in matches if f is not chosen][:3]
    for finding in analysis.findings:
        if finding is chosen or finding in supporting:
            continue
        if finding.dimension != routing.dimension:
            continue
        if finding.analysis_id.endswith(("largest", "concentration")):
            supporting.append(finding)
    return supporting[:4]


def answerable_concepts():
    """Everything `/ask-business-data` can be asked about, for a clarification reply."""
    return {"metrics": sorted(kpi_vocabulary()),
            "dimensions": sorted(dimension_vocabulary()),
            "intents": [name for name, _words in INTENTS]}
