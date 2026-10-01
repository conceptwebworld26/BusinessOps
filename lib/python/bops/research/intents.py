"""The research-intent registry: one declarative table, and the only one.

A research request names a **category** - what kind of thing is being researched - and an
**intent** - which question is being asked about it. Until M9-D.4 those two lived as a flat
tuple of identifiers plus two further flat structures elsewhere (`INTENT_TERMS` and
`SUBJECT_LEADS` in `query.py`), and the relationship between a category and the intents it
uses lived nowhere at all: it was recoverable only by reading three skill files. Adding an
intent therefore meant editing three structures in two modules and hoping none was missed.

This module replaces that with **one record per intent**, and derives the flat structures
from it. `INTENTS`, `INTENT_TERMS` and `SUBJECT_LEADS` still exist and still hold exactly
what they held before - they are now views of the registry rather than independent tables,
so they cannot drift from it or from each other. ADR-0021.

**This registry is metadata.** It performs no retrieval, calls no gate, dispatches no
scout, parses no evidence, creates no claim and synthesises nothing. Every one of those has
a home already, and a table that started calling them would be a framework rather than a
description. The only thing anything reads out of here is *what a question is called, how
it phrases itself, and which categories ask it*.

**It is immutable, and that is a security property, not tidiness.** Intent metadata decides
the wording that goes into a query, and a query's wording is what the disclosure gate
assesses. A registry a caller could edit at runtime would be a registry that untrusted
external content - or a competitor name typed by a user - could edit at runtime, and the
text assessed by the gate would then not be the text the registry described. `ResearchIntent`
is a namedtuple and the mappings are read-only proxies, so there is no write path at all.
Nothing here is ever built from user input: the table is closed, declared in source, and an
intent outside it is refused by `ResearchRequest.validate()` before the gate sees it.
"""

import collections
import types

# -- research categories -----------------------------------------------------

#: The four categories Milestone 9 covers. Recorded here once so the shared core is
#: category-agnostic: the company/market/competitor/industry skills parameterise this core
#: rather than each implementing their own request type. `contract.py` re-exports these, so
#: `contract.COMPANY` and every existing import of it continue to resolve.
COMPANY = "company"
MARKET = "market"
COMPETITOR = "competitor"
INDUSTRY = "industry"

CATEGORIES = (COMPANY, MARKET, COMPETITOR, INDUSTRY)

#: Categories with a production analysis skill. `INDUSTRY` joined in M9-D.5 exactly as
#: ADR-0021 said it would: `bops-industry-research` was built, so `industry` was added here
#: and the intents it asks added `INDUSTRY` to their `categories` field. Nothing else about
#: the registry changed, and no second table was needed to hold the new mappings.
ANALYSIS_CATEGORIES = (COMPANY, MARKET, COMPETITOR, INDUSTRY)

# -- research intent identifiers ---------------------------------------------
#
# The identifiers are the stable part of this module. They are what a skill writes, what a
# request validates against, what an audit record carries, and what a test pins. The
# metadata beside them may be described differently over time; a value here cannot change
# without changing behaviour, so none of them ever has.

BENCHMARK = "benchmark"          # "what is typical" - the Tier 0 workhorse
PROFILE = "profile"              # what is publicly known about one entity
SIZING = "sizing"                # how large is a market
TRENDS = "trends"                # what is changing
POSITIONING = "positioning"      # how entities compare publicly
OVERVIEW = "overview"            # what a market is: definition, scope, current state
DRIVERS = "drivers"              # what moves a market: demand, supply, constraints
LANDSCAPE = "landscape"          # who competes with whom, and on what terms
COMPARISON = "comparison"        # how named entities compare on observable dimensions
DEFINITION = "definition"        # what a subject is: scope, boundaries, participant kinds
STRUCTURE = "structure"          # how a subject is organised: value chain, supply, demand


#: One research question, fully described.
#:
#: A namedtuple rather than a frozen class because immutability is the entire requirement
#: and the stdlib already provides exactly that, with no `__setattr__` of our own to get
#: wrong. `Destination` earns its hand-written freeze by carrying an approval identity;
#: this record carries declared constants and needs nothing beyond a read-only field.
#:
#:   identifier     the stable intent string; the value a request and an audit record carry
#:   purpose        what the question asks, in a reader's words
#:   query_term     the words that express the intent inside the query text itself
#:   subject_leads  True where the query reads naturally with the subject first
#:   categories     the analysis categories that ask this question; () for none
#:   used_by        the production skills or commands that issue it today
ResearchIntent = collections.namedtuple(
    "ResearchIntent",
    "identifier purpose query_term subject_leads categories used_by")


#: The canonical table. Declaration order is the order `INTENTS` has always had, and the
#: order every derived view below inherits, so a derived tuple is byte-identical to the
#: literal it replaced.
#:
#: `TRENDS`, `POSITIONING`, `SIZING` and `DRIVERS` are each one identifier used by more than
#: one category, and that is deliberate (ADR-0020, reaffirmed by ADR-0021): a
#: category-specific twin of a question the table already asks would give one question two
#: names, which is precisely what a closed enumeration exists to prevent. Shared means
#: *shared identifier*, listed once with several categories - never duplicated per category.
#:
#: M9-D.5 added `DEFINITION` and `STRUCTURE` for `bops-industry-research` and reused
#: `SIZING`, `TRENDS` and `DRIVERS`, on the ADR-0019/ADR-0020 test: reuse where the question
#: is the same, add only where no existing intent's *query wording* expresses it.
#:
#:   * `SIZING`, `TRENDS`, `DRIVERS` - reused. "How large and how fast growing", "what is
#:     changing" and "what moves demand and supply" are the same questions for an industry
#:     as for a market, and their query wording retrieves industry sources unchanged. Their
#:     `purpose` text was widened to say "market or industry"; no `query_term` moved.
#:   * `DEFINITION` - new, because `OVERVIEW` renders as the literal words *market
#:     overview*, which sends an industry-definition question looking for market-research
#:     reports rather than classifications, trade bodies and industry associations. This is
#:     ADR-0019's own argument for why `PROFILE` ("company profile") could not serve a
#:     market: the wording is the retrieval.
#:   * `STRUCTURE` - new, because the nearest existing intent is `LANDSCAPE`, which renders
#:     as *competitive landscape* and would steer an industry-structure question into
#:     competitor research - the one thing `bops-industry-research` must not become.
#:
#: Neither new identifier is category-prefixed or -suffixed: both name the question, not the
#: category asking it, so either can be reused by a later category without a rename.
#:
#: `BENCHMARK` carries no category. It is the default intent of every `ResearchRequest` and
#: is category-agnostic by design - `/retrieval-slice` issues it against `INDUSTRY` - so
#: assigning it an owner would state something the code does not do.
_RECORDS = (
    ResearchIntent(
        identifier=BENCHMARK,
        purpose="what is typical - the Tier 0 workhorse",
        query_term="benchmark",
        subject_leads=False,
        categories=(),
        used_by=("/retrieval-slice",)),
    ResearchIntent(
        identifier=PROFILE,
        purpose="what is publicly known about one entity",
        query_term="company profile",
        subject_leads=True,
        categories=(COMPANY,),
        used_by=("bops-company-analysis",)),
    ResearchIntent(
        identifier=SIZING,
        purpose="how large is a market or industry, and how fast it is growing",
        query_term="market size",
        subject_leads=False,
        categories=(MARKET, INDUSTRY),
        used_by=("bops-market-analysis", "bops-industry-research")),
    ResearchIntent(
        identifier=TRENDS,
        purpose="what is changing",
        query_term="trends",
        subject_leads=False,
        categories=(COMPANY, MARKET, COMPETITOR, INDUSTRY),
        used_by=("bops-company-analysis", "bops-market-analysis",
                 "bops-competitor-analysis", "bops-industry-research")),
    ResearchIntent(
        identifier=POSITIONING,
        purpose="how entities compare publicly",
        query_term="market position",
        subject_leads=True,
        categories=(COMPANY, COMPETITOR),
        used_by=("bops-company-analysis", "bops-competitor-analysis")),
    ResearchIntent(
        identifier=OVERVIEW,
        purpose="what a market is: definition, scope, current state",
        query_term="market overview",
        subject_leads=False,
        categories=(MARKET,),
        used_by=("bops-market-analysis",)),
    ResearchIntent(
        identifier=DRIVERS,
        purpose="what moves a market or industry: demand, supply, constraints",
        query_term="market drivers and constraints",
        subject_leads=False,
        categories=(MARKET, INDUSTRY),
        used_by=("bops-market-analysis", "bops-industry-research")),
    ResearchIntent(
        identifier=LANDSCAPE,
        purpose="who competes with whom, and on what terms",
        query_term="competitive landscape",
        subject_leads=True,
        categories=(COMPETITOR,),
        used_by=("bops-competitor-analysis",)),
    ResearchIntent(
        identifier=COMPARISON,
        purpose="how named entities compare on observable dimensions",
        query_term="competitor comparison",
        subject_leads=True,
        categories=(COMPETITOR,),
        used_by=("bops-competitor-analysis",)),
    ResearchIntent(
        identifier=DEFINITION,
        purpose="what a subject is: scope, boundaries and the kinds of participant in it",
        query_term="industry definition and scope",
        subject_leads=False,
        categories=(INDUSTRY,),
        used_by=("bops-industry-research",)),
    ResearchIntent(
        identifier=STRUCTURE,
        purpose="how a subject is organised: value chain, supply and demand "
                "characteristics, barriers",
        query_term="industry structure and value chain",
        subject_leads=False,
        categories=(INDUSTRY,),
        used_by=("bops-industry-research",)),
)

_REGISTRY = collections.OrderedDict()
for _record in _RECORDS:
    if _record.identifier in _REGISTRY:
        raise RuntimeError("duplicate research intent %r" % _record.identifier)
    _REGISTRY[_record.identifier] = _record
del _record

#: Read-only view of the canonical table, keyed by intent identifier. A proxy rather than
#: the dict itself so a caller holding it cannot add, replace or delete an intent.
INTENT_REGISTRY = types.MappingProxyType(_REGISTRY)


# -- derived views -----------------------------------------------------------
#
# Everything below is computed from the registry. None of it is a second source of truth,
# and none may be hand-edited: changing an intent means changing its record above, and
# every view follows. They exist because callers already import these names, and a rename
# for elegance would be a breaking change bought with nothing (ADR-0021, Compatibility).

#: The closed, validated enumeration `ResearchRequest.validate()` checks against.
INTENTS = tuple(_REGISTRY)

#: Words that express the intent in the query itself.
INTENT_TERMS = types.MappingProxyType(
    {identifier: record.query_term for identifier, record in _REGISTRY.items()})

#: Intents whose query reads naturally with the subject first. An intent absent from this
#: tuple keeps the trailing-subject phrasing it always had, so no existing query moves by a
#: byte.
SUBJECT_LEADS = tuple(identifier for identifier, record in _REGISTRY.items()
                      if record.subject_leads)

#: Which questions each analysis category asks, derived from the `categories` field. The
#: relationship is many-to-many by construction: an intent lists every category that uses
#: it, and a category appears here once with every intent that named it.
CATEGORY_INTENTS = types.MappingProxyType(
    {category: tuple(identifier for identifier, record in _REGISTRY.items()
                     if category in record.categories)
     for category in ANALYSIS_CATEGORIES})


def intent(identifier):
    """The record for one intent, or `None` where the identifier is not registered.

    Returns `None` rather than raising: an unregistered intent is refused by
    `ResearchRequest.validate()` with a reason code, and a lookup here that raised first
    would replace that reason with a traceback.
    """
    return _REGISTRY.get(identifier)


def intents_for_category(category):
    """The intents one analysis category asks, in registry order.

    An unknown category - including `INDUSTRY`, which has no skill yet - returns an empty
    tuple. That is the honest answer: no intent claims it.
    """
    return CATEGORY_INTENTS.get(category, ())


def categories_for_intent(identifier):
    """The analysis categories that ask one intent, in `CATEGORIES` order.

    Empty for `BENCHMARK`, which is category-agnostic, and for an unregistered identifier.
    """
    record = _REGISTRY.get(identifier)
    return record.categories if record else ()
