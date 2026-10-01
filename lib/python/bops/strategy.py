# -*- coding: utf-8 -*-
"""Strategy recommendations: class-7 records grounded in a synthesis set, held beside it.

ADR-0031 decided the contract; this module is its engine. A recommendation is the one
statement in BusinessOps that proposes an action, so it is also the one most worth forging -
and the shape of the defence is the same as everywhere else in the synthesis stack: the
dangerous things have no field to occupy.

**What the skill authors.** Exactly six fields - `action`, `evidence`, `rationale`,
`expected_benefit`, `risks`, `dependencies`. Anything else, including `confidence`, a
priority, a score or a rank, is refused. **What this module derives.** Everything a reader
could be misled by: the confidence and its reasons, support, the domains the evidence rests
on, materiality, conflicts, limitations, caveats and the full per-evidence trail.

**How evidence is resolved.** Every evidence id must name exactly one statement in **one**
genuine strict `SynthesisSet`, and every statement is read through
`synthesis.grounding` - the single home ADR-0031 requires for the checks SWOT also applies.
A fact, a calculation, a sourced statement, or an interpretation whose recorded supports
really exist, precede it, reach evidence and account for its provenance. An assumption is
never evidence: it may only be named by a dependency, where it lowers confidence instead of
supporting anything. A recommendation has no synthesis id, so none can cite another.

**How confidence is derived.** `synthesis.confidence.combine()` over the reason codes the set
already derived for each cited statement and each cited assumption - the weakest level, every
reason pooled. No level or reason code is added, and nothing the skill writes can raise or
lower it.

**How figures are held to the evidence.** ADR-0002 says a reported figure is produced by
code, never by the model, so a recommendation may *quote* a figure and never *produce* one.
`figure_tokens()` below recognises numbers narrowly and `require_grounded()` refuses any that
the cited statements do not print. The exact rule is documented on those functions.

**What this module never does.** It reads no file, runs no analysis, retrieves nothing,
builds no evidence, foots no dimension, compares no values and changes the synthesis set in no
way. It executes no action: a recommendation is draft analysis for a person to decide on
(ADR-0010), and there is no field for an execution state because there is nothing to execute.
It re-enters nothing into synthesis either - the set refuses recommendation records at
`register_claims()` (ADR-0031, security constraint 6).
"""

import copy
import hashlib
import json
import re
import unicodedata
from decimal import Decimal

from . import evidence as evidence_mod
from . import quantity as quantity_mod
from .synthesis import confidence as confidence_mod
from .synthesis import contract as contract_mod
from .synthesis import grounding
from .synthesis import limitations as limitations_mod
from .synthesis import research_footing as footing_mod
from .synthesis import synthesis_set as set_mod

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "strategy"

#: The issuing capability (ADR-0031, *Decision owner*). Not a person.
ISSUED_BY = "bops-strategy-recommendations"

#: The only capabilities that may issue a class-7 record under this contract. ADR-0031 names
#: Decision Support as sharing it, with `issued_by` distinguishing the issuer (ADR-0032).
DECISION_SUPPORT_ISSUER = "bops-decision-support"
RECOMMENDATION_ISSUERS = (ISSUED_BY, DECISION_SUPPORT_ISSUER)


class StrategyError(contract_mod.SynthesisError):
    """A recommendation or its input violates ADR-0031. Raised, never degraded."""


#: The six fields a skill authors, in contract order. `confidence` is the sixth class-7 field
#: and is derived, so it is not here.
AUTHORED_FIELDS = ("action", "evidence", "rationale", "expected_benefit", "risks",
                   "dependencies")

#: A dependency record. `assumption_id` may be omitted on input and is always present on output.
DEPENDENCY_FIELDS = evidence_mod.RECOMMENDATION_DEPENDENCY_FIELDS

#: Evidence classes that satisfy ADR-0031's minimum basis directly: user data, external
#: sourced, calculated. An interpretation satisfies it only through its verified chain.
BASIS_CLASSES = (evidence_mod.USER_DATA, evidence_mod.EXTERNAL_SOURCED,
                 evidence_mod.CALCULATED)

EMPTY_STATE = "No supported recommendation identified."

HUMAN_DECISION = (
    "These recommendations are draft analysis for a person to decide on. BusinessOps does not "
    "execute any of them: carrying one out - a system write, a message, an export or an "
    "overwrite - needs that person's decision and explicit per-action approval, and financial "
    "transactions are prohibited.")

ORDER_NOTE = (
    "Recommendations appear in deterministic presentation order - by the position of each "
    "one's earliest cited statement in the synthesis set - which is not a ranking, a priority "
    "or an order of importance.")

#: Stated so a test can assert it.
EXECUTES_ACTIONS = False

_BUILD_TOKEN = object()


def _grounded(check, *args):
    """Run one shared grounding check, reporting its refusal as a `StrategyError`."""
    try:
        return check(*args)
    except grounding.GroundingError as refusal:
        raise StrategyError(str(refusal))


def recommendation_id(action, evidence):
    """Content-addressed from the action and the sorted evidence ids (ADR-0031)."""
    seed = "%s|%s" % (action, ",".join(sorted(evidence)))
    return "rec-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _digest(synthesis):
    """An immutable identity for the exact state of the set a result was grounded in."""
    return "sha256:" + hashlib.sha256(synthesis.to_json().encode("utf-8")).hexdigest()


def synthesis_digest(synthesis):
    """The public name for the set identity a `StrategyResult` binds to (ADR-0032 reuses it)."""
    return _digest(synthesis)


# ---------------------------------------------------------------------------
# Figures: quoted, never produced
# ---------------------------------------------------------------------------

#: A bare ISO date, year-month, or a four-digit year from 1900 to 2099.
_DATE = re.compile(
    r"(?<![A-Za-z0-9_.,\-/])"
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{4}-[0-9]{2}|(?:19|20)[0-9]{2})"
    r"(?![A-Za-z0-9_%]|[.,\-/][0-9])")

#: Text directly after a number that makes it a figure rather than a year.
_FIGURE_AFTER = re.compile(
    r"\s?(?:%|percent(?![A-Za-z])|pp(?![A-Za-z])|percentage points?(?![A-Za-z])|"
    r"(?:k|thousands?|m|mn|millions?|bn|billions?|tn|trillions?)(?![A-Za-z0-9_]))")

#: Text directly before a number that makes it a figure rather than a year.
_FIGURE_BEFORE = re.compile(r"(?:[$£€¥]-?|\b[A-Z]{3}\s-?)$")

_FIGURE = re.compile(r"""
    (?<![A-Za-z0-9_.,\-/])
    (?:(?P<code>[A-Z]{3})\s)?
    (?P<symbol>[$£€¥])?
    (?P<sign>-)?
    (?P<int>[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)
    (?:\.(?P<frac>[0-9]+))?
    (?:\s?(?P<scale>k|thousands?|m|mn|millions?|bn|billions?|tn|trillions?)(?![A-Za-z0-9_]))?
    (?:\s?(?P<unit>%|percent(?![A-Za-z])|pp(?![A-Za-z])|percentage\ points?(?![A-Za-z])))?
    (?:\s(?P<code2>[A-Z]{3})(?![A-Za-z0-9_]))?
    (?![A-Za-z0-9_]|[.,\-/][0-9])
""", re.X)

#: Characters that belong to an identifier-like word containing a digit.
_WORD_CHARS = re.compile(r"[A-Za-z0-9_.,\-/:#+]")

#: Cardinal number words. A figure written in words is still a figure (ADR-0031 rule 9), so a
#: number phrase must be printed as the same phrase by a cited statement. `one` alone is
#: deliberately not a figure: it is overwhelmingly a pronoun or determiner ("one of", "no one"),
#: and reading it as one would refuse ordinary prose without catching a quantity. Inside a phrase
#: ("twenty-one", "one hundred") it is part of the figure. Fractions and multipliers ("half",
#: "double") are not cardinals and stay qualitative, as M10.3.2 recorded.
NUMBER_WORDS = frozenset((
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "hundreds", "thousand", "thousands", "million", "millions", "billion", "billions",
    "trillion", "trillions", "dozen", "dozens"))
_PHRASE_WORDS = NUMBER_WORDS | frozenset(("one",))
_SCALE_WORDS = frozenset(("hundred", "hundreds", "thousand", "thousands", "million", "millions",
                          "billion", "billions", "trillion", "trillions"))
_LETTERS = re.compile(r"[A-Za-z]+")
_PHRASE_GAP = re.compile(r"[ \t-]+")
_AND_GAP = re.compile(r"[ \t]+")

#: Currency symbols read as a marker. `£` and `€` name one currency; `$` and `¥` name several,
#: so they match only the same symbol and never a code (ADR-0025: a bare `$` states no currency).
_SYMBOL_MARKER = {"£": "GBP", "€": "EUR", "$": "$", "¥": "¥"}

AMOUNT = "amount"
PERCENT = "percent"
PERCENTAGE_POINTS = "percentage_points"


def figure_tokens(text):
    """Every number-bearing token in `text`, classified. Refuses what it cannot read.

    The rule, exactly:

    1. **Dates.** `YYYY-MM-DD`, `YYYY-MM`, and a bare four-digit year from 1900 to 2099 are
       `("date", text)` - unless a currency marker precedes the year or a scale or percent
       follows it, in which case it is a figure. A date is never a figure and a figure is never
       a date, so a year in the evidence cannot ground an amount and an amount cannot ground a
       year.
    2. **Figures.** An optional three-letter currency code before or after, an optional currency
       symbol, an optional minus sign, digits (either plain or correctly grouped in threes with
       commas), an optional decimal part, an optional scale word from `bops.quantity`'s closed
       vocabulary (`k`, `thousand`, `m`, `mn`, `million`, `bn`, `billion`, `tn`, `trillion` and
       their plurals), and an optional `%`, `percent`, `pp` or `percentage point(s)`. It becomes
       `("figure", (kind, value, currency))`: `kind` is `percent`, `percentage_points` or
       `amount`; `value` is the exact `Decimal` - separators removed, scale multiplied in, sign
       applied - so `3500`, `3,500` and `3.5k` are the same value; `currency` is the code, `GBP`
       for `£`, `EUR` for `€`, and the literal symbol for `$` and `¥`. There is **no rounding**:
       `1.2 million` is not `1,210,775.23`.
    3. **Identifiers.** Any other run of characters containing a digit - `Q3`, `FY2026`,
       `v2.1.3`, `46-390`, `sy-7cf1c90f8c67`, a malformed grouping such as `1,2345` - is
       `("identifier", word)` and is never read as a figure.
    4. **Number words.** A run of cardinal words not already part of a figure (`3.47 million`
       is one figure) is one `("number_word", phrase)`: the words lower-cased and joined by single
       spaces, whether the source separated them with spaces or hyphens, with an `and` after a
       scale word dropped - so `Twenty-five` and `twenty five` are both `twenty five`, and `one
       hundred and five` is `one hundred five`. `one` on its own is not a figure. Added in
       M10.3.3: a figure written in words is still a figure, matched as a whole phrase, and never
       matches a numeral.

    A digit outside ASCII `0-9` is refused outright: a script whose numerals this rule cannot
    read is not a place to guess.
    """
    text = str(text or "")
    for char in text:
        if char.isdigit() and char not in "0123456789":
            raise StrategyError(
                "%r contains a numeral outside 0-9 (%s); figures are checked only where they "
                "can be read exactly" % (text, unicodedata.name(char, "unknown digit")))

    tokens = []
    covered = [False] * len(text)

    def cover(start, end):
        for i in range(start, end):
            covered[i] = True

    masked = list(text)
    for match in _DATE.finditer(text):
        start, end = match.span()
        if _FIGURE_BEFORE.search(text[:start]) or _FIGURE_AFTER.match(text, end):
            continue
        tokens.append((start, ("date", match.group("date"))))
        cover(start, end)
        for i in range(start, end):
            masked[i] = " "

    masked = "".join(masked)
    for match in _FIGURE.finditer(masked):
        start, end = match.span()
        if any(covered[start:end]):
            continue
        tokens.append((start, ("figure", _figure_value(match))))
        cover(start, end)

    i = 0
    while i < len(text):
        if text[i] in "0123456789" and not covered[i]:
            start = i
            while (start > 0 and not covered[start - 1]
                   and _WORD_CHARS.match(text[start - 1])):
                start -= 1
            end = i
            while end < len(text) and not covered[end] and _WORD_CHARS.match(text[end]):
                end += 1
            word = text[start:end].strip(".,-/:")
            tokens.append((start, ("identifier", word)))
            cover(start, end)
            i = end
        else:
            i += 1

    words = [(match.start(), match.end(), match.group(0).lower())
             for match in _LETTERS.finditer(text) if not any(covered[match.start():match.end()])]
    run = []

    def flush():
        if any(word in NUMBER_WORDS for _start, word in run):
            tokens.append((run[0][0], ("number_word", " ".join(word for _s, word in run))))
        del run[:]

    previous_end = None
    for k, (start, end, word) in enumerate(words):
        if word in _PHRASE_WORDS:
            if run and not _PHRASE_GAP.fullmatch(text[previous_end:start]):
                flush()
            run.append((start, word))
            previous_end = end
        elif (word == "and" and run and run[-1][1] in _SCALE_WORDS and k + 1 < len(words)
              and words[k + 1][2] in _PHRASE_WORDS
              and _AND_GAP.fullmatch(text[previous_end:start])
              and _AND_GAP.fullmatch(text[end:words[k + 1][0]])):
            previous_end = end
        else:
            flush()
    flush()

    return [token for _position, token in sorted(tokens, key=lambda pair: pair[0])]


def _figure_value(match):
    digits = match.group("int").replace(",", "")
    if match.group("frac"):
        digits += "." + match.group("frac")
    value = Decimal(digits)
    if match.group("scale"):
        value *= quantity_mod.scale_factor(match.group("scale"))
    if match.group("sign"):
        value = -value

    unit = (match.group("unit") or "").lower()
    if unit in ("%", "percent"):
        kind = PERCENT
    elif unit.startswith("p"):
        kind = PERCENTAGE_POINTS
    else:
        kind = AMOUNT

    markers = set()
    for code in (match.group("code"), match.group("code2")):
        if code:
            markers.add(code)
    if match.group("symbol"):
        markers.add(_SYMBOL_MARKER[match.group("symbol")])
    if len(markers) > 1:
        raise StrategyError(
            "%r names two currencies (%s); a figure with two currencies is not quoted, it is "
            "refused" % (match.group(0), ", ".join(sorted(markers))))
    currency = markers.pop() if markers else None
    return (kind, value.normalize(), currency)


def _evidence_tokens(texts):
    """Tokens a cited statement prints. A statement this rule cannot read grounds nothing."""
    figures, dates, words, number_words = [], set(), set(), set()
    for text in texts:
        try:
            tokens = figure_tokens(text)
        except StrategyError:
            continue
        for kind, value in tokens:
            if kind == "figure":
                figures.append(value)
            elif kind == "date":
                dates.add(value)
            elif kind == "number_word":
                number_words.add(value)
            else:
                words.add(value)
    return figures, dates, words, number_words


def require_grounded(field, text, cited_texts, cited_ids=()):
    """Refuse `text` if it prints a figure, date or identifier the cited statements do not.

    Grounding, exactly:

    * a **figure** is grounded by a cited figure of the same kind and exactly the same value.
      If the recommendation names a currency, the cited figure must name the same one. If it
      names none, every cited figure with that kind and value must agree on its currency -
      otherwise the reference is ambiguous and refused;
    * a **date** is grounded by the same date in a cited statement; a year is also grounded by
      a cited date in that year;
    * an **identifier** is grounded by the same word in a cited statement, or by being one of
      the cited statement ids.

    Only the statements passed in count. A figure printed in a statement the recommendation
    does not cite grounds nothing.
    """
    figures, dates, words, number_words = _evidence_tokens(cited_texts)
    words |= set(cited_ids)
    for kind, value in figure_tokens(text):
        if kind == "figure":
            f_kind, f_value, f_currency = value
            matches = [c for c in figures if c[0] == f_kind and c[1] == f_value]
            if f_currency is not None:
                matches = [c for c in matches if c[2] == f_currency]
            elif len(set(c[2] for c in matches)) > 1:
                raise StrategyError(
                    "the %s figure %s matches cited figures in more than one currency (%s); "
                    "name the currency the cited statement prints"
                    % (field, f_value, ", ".join(sorted(str(c[2]) for c in matches))))
            if not matches:
                raise StrategyError(
                    "the %s states a figure (%s %s%s) that no cited statement prints. A "
                    "recommendation quotes figures from its evidence and never produces one "
                    "(ADR-0002, ADR-0031)."
                    % (field, f_kind, f_value, " " + f_currency if f_currency else ""))
        elif kind == "date":
            if value not in dates and not (len(value) == 4 and any(
                    d.startswith(value + "-") for d in dates)):
                raise StrategyError(
                    "the %s names the date %s, which no cited statement prints" % (field, value))
        elif kind == "number_word":
            if value not in number_words:
                raise StrategyError(
                    "the %s writes the figure %r in words, which no cited statement prints as "
                    "the same phrase; a figure in words is still a figure and is quoted or left "
                    "out" % (field, value))
        elif value not in words:
            raise StrategyError(
                "the %s contains %r, which no cited statement prints; a number-bearing word "
                "is quoted from the evidence or left out" % (field, value))


# ---------------------------------------------------------------------------
# Authored fields
# ---------------------------------------------------------------------------

def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _authored(raw):
    """The six authored fields, shape-checked and normalised, or a refusal."""
    if not isinstance(raw, dict):
        raise StrategyError(
            "a proposed recommendation is a record of %s; %r is not one"
            % (", ".join(AUTHORED_FIELDS), type(raw).__name__))
    extra = sorted(set(raw) - set(AUTHORED_FIELDS))
    if extra:
        raise StrategyError(
            "a recommendation is authored with exactly %s; %s is not accepted. Confidence, "
            "support and every other conclusion are derived, and there is no priority, rank, "
            "score or weight to supply." % (", ".join(AUTHORED_FIELDS),
                                              ", ".join(str(e) for e in extra)))
    missing = [name for name in AUTHORED_FIELDS if name not in raw]
    if missing:
        raise StrategyError("a recommendation must state %s" % ", ".join(missing))

    for name in ("action", "rationale", "expected_benefit"):
        if not _text(raw[name]):
            raise StrategyError("a recommendation's %s must be non-empty text" % name)

    evidence = raw["evidence"]
    if not isinstance(evidence, (list, tuple)) or not evidence:
        raise StrategyError(
            "a recommendation's evidence is a non-empty list of synthesis statement ids; a "
            "recommendation with no evidence is not issued")
    if not all(isinstance(e, str) for e in evidence):
        raise StrategyError("evidence ids are strings naming synthesis statements")
    if len(set(evidence)) != len(evidence):
        raise StrategyError("a recommendation cites each evidence statement once")

    risks = raw["risks"]
    if not isinstance(risks, (list, tuple)) or not risks or not all(_text(r) for r in risks):
        raise StrategyError(
            "a recommendation's risks are a non-empty list of non-empty text; an action with "
            "no stated risk is not issued")

    dependencies = raw["dependencies"]
    if not isinstance(dependencies, (list, tuple)) or not dependencies:
        raise StrategyError(
            "a recommendation's dependencies are a non-empty list; every action depends at "
            "least on its evidence remaining current and correctly scoped")
    normalised = []
    for entry in dependencies:
        if not isinstance(entry, dict):
            raise StrategyError("a dependency is a record of text and, optionally, assumption_id")
        unknown = sorted(set(entry) - set(DEPENDENCY_FIELDS))
        if unknown:
            raise StrategyError("a dependency carries only %s; %s is not accepted"
                                % (", ".join(DEPENDENCY_FIELDS), ", ".join(unknown)))
        if not _text(entry.get("text")):
            raise StrategyError("a dependency's text must be non-empty")
        assumption_id = entry.get("assumption_id")
        if assumption_id is not None and not isinstance(assumption_id, str):
            raise StrategyError("a dependency's assumption_id is a synthesis statement id")
        normalised.append({"text": entry["text"], "assumption_id": assumption_id})

    return {"action": raw["action"], "evidence": list(evidence),
            "rationale": raw["rationale"], "expected_benefit": raw["expected_benefit"],
            "risks": list(risks), "dependencies": normalised}


# ---------------------------------------------------------------------------
# One recommendation
# ---------------------------------------------------------------------------

def _statement_detail(synthesis, index, position, item):
    record = item.as_dict()
    supports = []
    if item.kind == contract_mod.INTERPRETATION:
        for _position, support in _grounded(grounding.interpretation_supports, index,
                                            position, item):
            supports.append({"synthesis_id": support.id, "kind": support.kind,
                             "domain": support.domain, "origin": support.origin,
                             "statement": support.statement})
    return {
        "synthesis_id": item.id,
        "kind": item.kind,
        "evidence_class": item.evidence_class,
        "origin": item.origin,
        "domain": item.domain,
        "trust": item.trust,
        "statement": item.statement,
        "support": item.support,
        "confidence": item.confidence,
        "confidence_reasons": list((item.confidence_detail or {}).get("reasons") or []),
        "material": item.is_material,
        "materiality": record.get("materiality"),
        "conflict_refs": sorted(item.conflict_refs),
        "unresolved_dimensions": (footing_mod.dimension_report(item)[1]
                                  if item.dimension_provenance else {}),
        "chain": synthesis.chain(item),
        "supports": supports,
    }


def cite(index, synthesis_id):
    """`(position, item, domains)` for one evidence id under ADR-0031's rules, or a refusal.

    The single evidence-citation rule for class-7 records and, through ADR-0032, for every part
    of a decision package that cites evidence: exactly one statement in the set, never an
    assumption, and readable as evidence by the shared grounding checks.
    """
    position, item = _grounded(grounding.one, index, synthesis_id)
    if grounding.graded(item) and item.kind == contract_mod.ASSUMPTION:
        raise StrategyError(
            "evidence %s is an assumption. An assumption is never evidence; name it as a "
            "dependency's assumption_id, where it lowers confidence instead of supporting "
            "the action (ADR-0031)." % synthesis_id)
    domains = _grounded(grounding.evidence_domains, index, position, item)
    return position, item, domains


def statement_detail(synthesis, index, position, item):
    """The ADR-0031 per-statement evidence detail, shared by every class-7 consumer."""
    return _statement_detail(synthesis, index, position, item)


def ground_recommendation(synthesis, index, raw, issued_by=ISSUED_BY):
    """One class-7 record grounded in `synthesis`: `(first_position, record)`, or a refusal.

    The one home of the record rules (ADR-0031). `issued_by` must be one of
    `RECOMMENDATION_ISSUERS`; nothing else about the record changes with the issuer.
    """
    return _recommendation(synthesis, index, raw, issued_by=issued_by)


def _recommendation(synthesis, index, raw, issued_by=ISSUED_BY):
    """`(first_position, record)` for one proposal, or a `StrategyError`."""
    if issued_by not in RECOMMENDATION_ISSUERS:
        raise StrategyError("%r is not a capability that issues recommendations; issuers are "
                            "%s" % (issued_by, ", ".join(RECOMMENDATION_ISSUERS)))
    fields = _authored(raw)

    cited = [cite(index, synthesis_id) for synthesis_id in fields["evidence"]]

    basis = [item for _position, item, domains in cited
             if domains and (item.evidence_class in BASIS_CLASSES
                             or item.kind == contract_mod.INTERPRETATION)]
    if not basis:
        raise StrategyError(
            "no cited statement is class 1, 3 or 4 or an interpretation whose chain reaches "
            "one; a recommendation without an evidential basis is not issued")

    assumptions = []
    for dependency in fields["dependencies"]:
        assumption_id = dependency["assumption_id"]
        if assumption_id is None:
            continue
        _position, item = _grounded(grounding.one, index, assumption_id)
        if not grounding.graded(item) or item.kind != contract_mod.ASSUMPTION:
            raise StrategyError(
                "dependency assumption_id %s names a %s, not an assumption the set registered"
                % (assumption_id, getattr(item, "kind", type(item).__name__)))
        if item not in assumptions:
            assumptions.append(item)

    cited_items = [item for _position, item, _domains in cited]
    cited_texts = [item.statement for item in cited_items]
    cited_ids = [item.id for item in cited_items]
    require_grounded("action", fields["action"], cited_texts, cited_ids)
    require_grounded("rationale", fields["rationale"], cited_texts, cited_ids)
    require_grounded("expected_benefit", fields["expected_benefit"], cited_texts, cited_ids)
    for risk in fields["risks"]:
        require_grounded("risks", risk, cited_texts, cited_ids)
    by_id = dict((item.id, item) for item in assumptions)
    for dependency in fields["dependencies"]:
        own = by_id.get(dependency["assumption_id"])
        require_grounded("dependencies", dependency["text"],
                         cited_texts + ([own.statement] if own is not None else []),
                         cited_ids + ([own.id] if own is not None else []))

    contributing = cited_items + assumptions
    assessment = confidence_mod.combine([
        confidence_mod.assess((item.confidence_detail or {}).get("reasons") or [])
        for item in contributing])

    conflicts_by_id = dict((conflict.id, conflict) for conflict in synthesis.conflicts)
    conflict_ids = []
    for item in contributing:
        for conflict_id in sorted(item.conflict_refs):
            if conflict_id not in conflict_ids:
                conflict_ids.append(conflict_id)

    caveats = []
    for item in contributing:
        for caveat in item.caveats:
            if caveat not in caveats:
                caveats.append(caveat)

    rec_id = recommendation_id(fields["action"], fields["evidence"])
    record = {
        "recommendation_id": rec_id,
        "issued_by": issued_by,
        "provenance_class": evidence_mod.RECOMMENDATION,
        "label": "RECOMMENDATION",
        "action": fields["action"],
        "evidence": fields["evidence"],
        "rationale": fields["rationale"],
        "expected_benefit": fields["expected_benefit"],
        "risks": fields["risks"],
        "dependencies": fields["dependencies"],
        "confidence": assessment.level,
        "confidence_reasons": list(assessment.reasons),
        "support": contract_mod.weakest_support([item.support for item in cited_items]),
        "rests_on": sorted(set().union(*[domains for _p, _i, domains in cited])),
        "material": any(item.is_material for item in cited_items),
        "evidence_detail": [_statement_detail(synthesis, index, position, item)
                            for position, item, _domains in cited],
        "assumptions": [{"synthesis_id": item.id, "statement": item.statement,
                         "support": item.support, "confidence": item.confidence,
                         "confidence_reasons": list(
                             (item.confidence_detail or {}).get("reasons") or [])}
                        for item in assumptions],
        "conflicts": [conflicts_by_id[c].as_dict() for c in conflict_ids
                      if c in conflicts_by_id],
        "limitations": limitations_mod.as_dicts(limitations_mod.merge(
            *[item.limitations for item in contributing])),
        "caveats": caveats,
    }
    _claim(record)
    first_position = min(position for position, _item, _domains in cited)
    return first_position, record


def _claim(record):
    """The class-7 ledger form. Built here so a record `Claim` would refuse is never emitted."""
    try:
        return evidence_mod.Claim(
            record["action"], evidence_mod.RECOMMENDATION,
            confidence=record["confidence"], based_on=list(record["evidence"]),
            caveats=list(record["caveats"]),
            evidence=list(record["evidence"]), rationale=record["rationale"],
            expected_benefit=record["expected_benefit"], risks=list(record["risks"]),
            dependencies=[dict(d) for d in record["dependencies"]])
    except evidence_mod.LedgerError as refusal:
        raise StrategyError(str(refusal))


# ---------------------------------------------------------------------------
# The result
# ---------------------------------------------------------------------------

class StrategyResult:
    """Recommendations grounded in one genuine strict synthesis set, held beside it.

    Built only by `build()`. It holds the set object itself - never a serialised copy - and a
    digest of the set's exact state when the recommendations were grounded, so a set that
    changed afterwards cannot lend its authority to recommendations it no longer supports.
    """

    __slots__ = ("_synthesis", "_records", "_digest", "_proposals")

    def __init__(self, synthesis, records, digest, proposals=(), _token=None):
        if _token is not _BUILD_TOKEN:
            raise StrategyError(
                "a StrategyResult is built by strategy.build() from a genuine synthesis set; "
                "records assembled elsewhere were never resolved against one")
        self._synthesis = synthesis
        self._records = records
        self._digest = digest
        self._proposals = copy.deepcopy(list(proposals))

    @property
    def proposals(self):
        """Copies of the proposals these records were grounded from, as supplied. Read-only.

        Retained so the M11 verifier can rebuild the result through `build()` and require
        byte-identical records (ADR-0034 section 5.2); nothing else reads them.
        """
        return copy.deepcopy(self._proposals)

    @property
    def synthesis(self):
        """The set these recommendations were grounded in. Read it; never write to it."""
        return self._synthesis

    @property
    def synthesis_digest(self):
        return self._digest

    @property
    def recommendations(self):
        """Copies, in presentation order. Editing one changes nothing here."""
        return copy.deepcopy(self._records)

    def is_bound_to(self, synthesis):
        """True only for the same set object, unchanged since the result was built."""
        return synthesis is self._synthesis and _digest(synthesis) == self._digest

    def _require_bound(self):
        if not self.is_bound_to(self._synthesis):
            raise StrategyError(
                "the synthesis set changed after these recommendations were grounded; build "
                "them again rather than carrying their confidence onto different evidence")

    def claims(self):
        """The class-7 `evidence.Claim` for each recommendation, in presentation order."""
        self._require_bound()
        return [_claim(record) for record in self._records]

    def record_in(self, ledger):
        """Append each recommendation's class-7 claim to an evidence ledger."""
        return [ledger.add(claim) for claim in self.claims()]

    def as_dict(self):
        self._require_bound()
        synthesis = self._synthesis
        cited = set()
        for record in self._records:
            cited.update(record["evidence"])
        return {
            "schema_version": SCHEMA_VERSION,
            "analysis": ANALYSIS,
            "issued_by": ISSUED_BY,
            "subject": synthesis.subject,
            "as_of": synthesis.as_of,
            "business_model": synthesis.business_model,
            "currency": synthesis.currency,
            "quality_grade": synthesis.quality_grade,
            "synthesis_digest": self._digest,
            "trust_statement": set_mod.TRUST_STATEMENT,
            "human_decision": HUMAN_DECISION,
            "order_note": ORDER_NOTE,
            "recommendations": copy.deepcopy(self._records),
            "empty_state": None if self._records else EMPTY_STATE,
            "material_not_cited": [item.id for item in synthesis.material()
                                   if item.id not in cited],
            "conflicts": [conflict.as_dict() for conflict in synthesis.conflicts],
            "limitations": limitations_mod.as_dicts(synthesis.limitations),
            "confidence": synthesis.confidence().as_dict(),
        }

    def to_json(self, indent=None):
        """Deterministic serialisation: sorted keys, JSON-safe throughout."""
        return json.dumps(self.as_dict(), sort_keys=True, indent=indent, default=str)

    def __repr__(self):
        return "StrategyResult(%d recommendations)" % len(self._records)


def candidates(synthesis):
    """Every statement in the set and the role it may play in a recommendation. Read-only.

    `evidence` where it passes the shared grounding checks, `assumption` for a registered
    assumption a dependency may name, `ineligible` with the refusal otherwise.
    """
    synthesis = _grounded(grounding.genuine_set, synthesis)
    index = grounding.index(synthesis)
    listed = []
    for position, item in enumerate(synthesis.items):
        entry = {"synthesis_id": item.id, "kind": item.kind, "domain": item.domain,
                 "origin": item.origin, "statement": item.statement,
                 "support": item.support, "confidence": item.confidence,
                 "material": item.is_material, "role": "ineligible", "reason": None}
        try:
            grounding.one(index, item.id)
            if item.kind == contract_mod.ASSUMPTION:
                entry["role"] = "assumption"
            else:
                grounding.evidence_domains(index, position, item)
                entry["role"] = "evidence"
        except grounding.GroundingError as refusal:
            entry["reason"] = str(refusal)
        listed.append(entry)
    return listed


def build(synthesis, proposals):
    """Ground each proposed recommendation in one genuine strict set and return the result.

    Every proposal is checked; the first that fails raises `StrategyError` and nothing is
    returned, so a partly grounded strategy is never presented as a whole one. An empty list
    yields a result with the explicit empty state. The set is read and never modified.
    """
    synthesis = _grounded(grounding.genuine_set, synthesis)
    if not isinstance(proposals, (list, tuple)):
        raise StrategyError("proposals are a list of records, one per recommendation")

    index = grounding.index(synthesis)
    before = _digest(synthesis)
    built, seen = [], set()
    for raw in proposals:
        first_position, record = _recommendation(synthesis, index, raw)
        if record["recommendation_id"] in seen:
            raise StrategyError(
                "recommendation %s is proposed twice; the same action on the same evidence is "
                "one recommendation" % record["recommendation_id"])
        seen.add(record["recommendation_id"])
        built.append((first_position, record["recommendation_id"], record))

    if _digest(synthesis) != before:
        raise StrategyError("the synthesis set changed while recommendations were grounded")
    records = [record for _p, _r, record in sorted(built, key=lambda t: (t[0], t[1]))]
    return StrategyResult(synthesis, records, before, proposals=proposals,
                          _token=_BUILD_TOKEN)


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def render(result):
    """The strategy analysis as markdown, formatted once. Adds no sentence of analysis.

    Every line is a heading, an authored field, a statement already in the set, or a label for
    something the result carries. There is no score, rank, priority, "top" recommendation or
    execution status to render, because the result has none.
    """
    record = result.as_dict() if isinstance(result, StrategyResult) else result
    lines = ["# Strategy analysis — %s" % (record.get("subject") or "subject not stated"), ""]
    basis = [("Business model", record.get("business_model")),
             ("Currency", record.get("currency")),
             ("As of", record.get("as_of")),
             ("Data quality", record.get("quality_grade"))]
    stated = ["%s: %s" % (label, value) for label, value in basis if value]
    if stated:
        lines += [" · ".join(stated), ""]
    lines += ["> %s" % record["human_decision"], ""]

    confidence = record["confidence"]
    lines.append("**Synthesis confidence:** %s" % confidence["confidence"])
    for explanation in confidence.get("explanations") or []:
        lines.append("- %s" % explanation)
    lines.append("")
    if record["limitations"]:
        lines.append("**Limitations** (%d)" % len(record["limitations"]))
        for limitation in record["limitations"]:
            lines.append("- `%s` %s — %s" % (limitation["code"],
                                             limitation.get("subject") or "",
                                             limitation.get("reason") or ""))
        lines.append("")
    if record["conflicts"]:
        lines.append("**Unresolved conflicts** (%d)" % len(record["conflicts"]))
        for conflict in record["conflicts"]:
            lines.append("- `%s` %s — %s" % (conflict["conflict_id"], conflict["subject"],
                                             conflict.get("reason") or ""))
        lines.append("")

    lines += ["## Recommendations", "", "_%s_" % record["order_note"], ""]
    if not record["recommendations"]:
        lines += ["_%s_" % record["empty_state"], ""]
    for rec in record["recommendations"]:
        lines += ["### `%s`" % rec["recommendation_id"], ""]
        lines.append("**Action:** %s" % rec["action"])
        lines.append("**Confidence:** %s%s" % (
            rec["confidence"],
            " — %s" % ", ".join(rec["confidence_reasons"]) if rec["confidence_reasons"] else ""))
        lines.append("**Support:** %s · rests on %s%s" % (
            rec["support"], ", ".join(rec["rests_on"]),
            " · material" if rec["material"] else ""))
        lines += ["", "**Evidence**"]
        for detail in rec["evidence_detail"]:
            lines.append("- `%s` [%s · %s · %s · %s] %s" % (
                detail["synthesis_id"], detail["kind"], detail["domain"], detail["support"],
                detail["confidence"], detail["statement"]))
            for entry in detail["chain"]:
                lines.append("  - rests on `%s:%s`%s" % (
                    entry["kind"], entry["ref_id"],
                    " — %s, tier %s, %s" % (entry["source"], entry["source_tier"],
                                            entry.get("publication_date") or "undated")
                    if entry.get("source") else ""))
            for support in detail["supports"]:
                lines.append("  - reads `%s` (%s, %s)" % (support["synthesis_id"],
                                                          support["kind"],
                                                          support["domain"]))
            if detail["unresolved_dimensions"]:
                lines.append("  - unresolved dimensions: %s" % ", ".join(
                    "%s (%s)" % pair for pair in sorted(
                        detail["unresolved_dimensions"].items())))
        lines += ["", "**Rationale:** %s" % rec["rationale"],
                  "**Expected benefit:** %s" % rec["expected_benefit"], "", "**Risks**"]
        lines += ["- %s" % risk for risk in rec["risks"]]
        lines += ["", "**Dependencies**"]
        assumed = dict((a["synthesis_id"], a) for a in rec["assumptions"])
        for dependency in rec["dependencies"]:
            aid = dependency["assumption_id"]
            lines.append("- %s%s" % (
                dependency["text"],
                " (assumption `%s`: %s)" % (aid, assumed[aid]["statement"])
                if aid in assumed else ""))
        if rec["conflicts"]:
            lines += ["", "**Conflicts**"]
            for conflict in rec["conflicts"]:
                lines.append("- `%s` %s — %s" % (conflict["conflict_id"],
                                                 conflict["subject"],
                                                 conflict.get("reason") or ""))
        if rec["limitations"]:
            lines += ["", "**Limitations**"]
            for limitation in rec["limitations"]:
                lines.append("- `%s` %s — %s" % (limitation["code"],
                                                 limitation.get("subject") or "",
                                                 limitation.get("reason") or ""))
        if rec["caveats"]:
            lines += ["", "**Caveats**"]
            lines += ["- %s" % caveat for caveat in rec["caveats"]]
        lines.append("")

    if record["material_not_cited"]:
        lines.append("**Material statements not cited:** %s"
                     % ", ".join("`%s`" % i for i in record["material_not_cited"]))
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "build", "candidates", "render", "figure_tokens", "require_grounded",
    "recommendation_id", "StrategyResult", "StrategyError",
    "cite", "statement_detail", "ground_recommendation", "synthesis_digest",
    "DECISION_SUPPORT_ISSUER", "RECOMMENDATION_ISSUERS", "NUMBER_WORDS",
    "SCHEMA_VERSION", "ANALYSIS", "ISSUED_BY", "AUTHORED_FIELDS", "DEPENDENCY_FIELDS",
    "BASIS_CLASSES", "EMPTY_STATE", "HUMAN_DECISION", "ORDER_NOTE", "EXECUTES_ACTIONS",
    "AMOUNT", "PERCENT", "PERCENTAGE_POINTS",
]
