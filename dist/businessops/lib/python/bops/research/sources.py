"""Source quality, freshness and disagreement - the three ways external evidence goes wrong.

Implements `reference/research-policy.md`. The policy is the single home for these rules;
this module is the enforcement, and the tables below are the policy's own, not a second
opinion.

Three rules earn their keep by refusing something:

  * **Tier D is excluded.** Not "weighted down" - excluded. An unattributable or
    AI-generated page is not a weak source, it is not a source, and `accepted()` will not
    return one.
  * **Tier C cannot stand alone.** Vendor marketing corroborates; it does not establish. A
    material claim resting only on tier C is unsupported, which is a different outcome from
    unsourced and is reported as such.
  * **Stale is labelled, never discarded.** A three-year-old market size is still evidence
    of what was true three years ago. What it may not do is present itself as current.

Conflicts are represented rather than resolved. Averaging two market sizes produces a third
number nobody published, which is the most confident-looking way to be wrong.
"""

import datetime

from ..evidence import SOURCE_TIERS as CLAIMABLE_TIERS

# -- source tiers ------------------------------------------------------------

TIER_A = "A"
TIER_B = "B"
TIER_C = "C"
TIER_D = "D"

TIERS = (TIER_A, TIER_B, TIER_C, TIER_D)

#: What each tier may be used for. The values are the policy's words.
TIER_USE = {
    TIER_A: "quotable as fact with attribution",
    TIER_B: "quotable with attribution and date",
    TIER_C: "corroboration only - never the sole source for a material claim",
    TIER_D: "excluded",
}

TIER_DESCRIPTION = {
    TIER_A: "regulatory filings, official statistics, central banks, registries",
    TIER_B: "established industry research houses, major business press, trade bodies, "
            "registered first-party company sources",
    TIER_C: "vendor marketing, blogs, aggregators, undated pages",
    TIER_D: "unattributable, AI-generated, content farms",
}

#: Tiers that may support a claim at all. Sourced from `evidence.SOURCE_TIERS` so the
#: research layer and the claim ledger cannot drift apart about what D means.
USABLE_TIERS = tuple(CLAIMABLE_TIERS)

#: Tiers that may be the *sole* support for a material claim.
SOLE_SUPPORT_TIERS = (TIER_A, TIER_B)

EXCLUDED_TIER = TIER_D

# -- staleness ---------------------------------------------------------------

FINANCIALS = "financials"
MARKET_SIZING = "market_sizing"
POSITIONING = "positioning"

#: Days beyond which a claim of this kind is dated, from `reference/research-policy.md`.
STALENESS_DAYS = {
    FINANCIALS: 365,
    MARKET_SIZING: 730,
    POSITIONING: 545,
}

#: Used when a claim kind is not one of the three named. Conservative on purpose: the
#: shortest window applies, so an unclassified claim ages fastest rather than slowest.
DEFAULT_CLAIM_KIND = FINANCIALS

CURRENT = "current"
DATED = "dated"
UNDATED = "undated"

FRESHNESS = (CURRENT, DATED, UNDATED)


class SourceTierError(Exception):
    """A source tier is missing or invalid where one is required."""


def normalise_tier(tier):
    """Uppercase a tier, or raise. A tier is never inferred when evidence is insufficient."""
    if tier is None:
        raise SourceTierError(
            "source tier is required; it is not inferred when evidence is insufficient")
    value = str(tier).strip().upper()
    if value not in TIERS:
        raise SourceTierError("unknown source tier %r; expected one of %s"
                              % (tier, ", ".join(TIERS)))
    return value


def is_usable(tier):
    """Whether a source of this tier may support a claim at all."""
    return normalise_tier(tier) in USABLE_TIERS


def may_stand_alone(tier):
    """Whether this tier may be the only support for a material claim."""
    return normalise_tier(tier) in SOLE_SUPPORT_TIERS


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def staleness_window(claim_kind):
    """Days before a claim of this kind is dated."""
    return STALENESS_DAYS.get(claim_kind, STALENESS_DAYS[DEFAULT_CLAIM_KIND])


def assess_freshness(publication_date, claim_kind=DEFAULT_CLAIM_KIND, as_of=None):
    """Classify one source's age. Deterministic given `as_of`.

    `as_of` is a parameter rather than `today()` so a fixture test asserts a fixed answer;
    the caller supplies the reference date and the result never depends on when the suite
    happens to run.
    """
    window = staleness_window(claim_kind)
    published = _as_date(publication_date)
    reference = _as_date(as_of) or datetime.date.today()

    if published is None:
        return {"freshness": UNDATED, "age_days": None, "window_days": window,
                "claim_kind": claim_kind,
                "statement": ("No publication date; the claim cannot be shown to be "
                              "current and is treated as undated.")}

    age = (reference - published).days
    if age <= window:
        return {"freshness": CURRENT, "age_days": age, "window_days": window,
                "claim_kind": claim_kind,
                "statement": "Published %d days before the reference date, inside the "
                             "%d-day window for %s." % (age, window, claim_kind)}
    return {"freshness": DATED, "age_days": age, "window_days": window,
            "claim_kind": claim_kind,
            "statement": ("Published %d days before the reference date, beyond the %d-day "
                          "window for %s. It is evidence of what was true then, and must "
                          "not be presented as current." % (age, window, claim_kind))}


def is_stale(publication_date, claim_kind=DEFAULT_CLAIM_KIND, as_of=None):
    return assess_freshness(publication_date, claim_kind, as_of)["freshness"] != CURRENT


# ---------------------------------------------------------------------------
# Support adequacy
# ---------------------------------------------------------------------------

SUPPORTED = "supported"
CORROBORATION_ONLY = "corroboration_only"
UNSUPPORTED = "unsupported"


def assess_support(tiers, material=True):
    """Whether a set of source tiers adequately supports a claim.

    `material` matters: the policy restricts tier C from being the sole source for a
    *material* claim. A passing mention that nobody will act on is a different case, and
    conflating the two would either block ordinary colour or wave through a headline
    number resting on a vendor blog.
    """
    usable = [normalise_tier(t) for t in tiers if is_usable(t)]
    excluded = [normalise_tier(t) for t in tiers if not is_usable(t)]

    if not usable:
        return {"support": UNSUPPORTED, "usable_tiers": [], "excluded_tiers": excluded,
                "reason": ("No usable source. Tier D material is excluded and cannot "
                           "support a claim." if excluded else
                           "No source was captured for this claim.")}

    if any(may_stand_alone(t) for t in usable):
        return {"support": SUPPORTED, "usable_tiers": sorted(usable),
                "excluded_tiers": excluded,
                "reason": "Supported by at least one tier A or B source."}

    # Only tier C remains.
    if material:
        return {"support": UNSUPPORTED, "usable_tiers": sorted(usable),
                "excluded_tiers": excluded,
                "reason": ("Only tier C sources are available. Tier C corroborates but is "
                           "never the sole support for a material claim.")}
    return {"support": CORROBORATION_ONLY, "usable_tiers": sorted(usable),
            "excluded_tiers": excluded,
            "reason": "Tier C only; adequate for corroboration, not for a material claim."}


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

AGREES = "agrees"
CONFLICTS = "conflicts"
SINGLE = "single_source"

#: Relative difference beyond which two figures are treated as materially disagreeing.
#: A published range and a rounded restatement of the same study should not read as a
#: conflict; a doubling should.
CONFLICT_THRESHOLD_PCT = 20.0


class SourcePosition:
    """What one source says, kept whole so a conflict can be shown rather than resolved."""

    __slots__ = ("evidence_id", "value", "unit", "source", "source_tier", "source_date",
                 "definition", "scope", "freshness")

    def __init__(self, evidence_id, value, source, source_tier, source_date=None,
                 unit=None, definition=None, scope=None, freshness=None):
        self.evidence_id = evidence_id
        self.value = value
        self.unit = unit
        self.source = source
        self.source_tier = normalise_tier(source_tier)
        self.source_date = source_date
        self.definition = definition
        self.scope = scope
        self.freshness = freshness

    def as_dict(self):
        record = {"evidence_id": self.evidence_id, "value": self.value, "unit": self.unit,
                  "source": self.source, "source_tier": self.source_tier,
                  "source_date": self.source_date, "definition": self.definition,
                  "scope": self.scope, "freshness": self.freshness}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "SourcePosition(%s=%s, tier %s)" % (self.source, self.value,
                                                   self.source_tier)


def _numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def assess_conflict(positions, threshold_pct=CONFLICT_THRESHOLD_PCT, declared=False,
                    reason=None):
    """Compare what several sources say. Never averages, never picks a winner.

    Returns a structured record carrying every position intact, so the disagreement
    survives into summarisation instead of being silently collapsed at the first
    opportunity to make the output tidy.

    `declared=True` means the research layer **observed** the disagreement and is reporting
    it, rather than asking this function to find one. The distinction is the whole of
    M9-C.4 (ADR-0016): the numeric test below can only see figures, and two sources can
    disagree about what a figure *means* while reporting nearly the same number - the M9-B
    live retrieval found exactly that. So a declared conflict is never downgraded to
    `AGREES`, and the numeric assessment is kept alongside it rather than discarded.

    What `declared` does **not** do is let anything invent a conflict from prose. The
    caller must supply two or more positions, each tied to an evidence item that is already
    in the set; that validation lives in `handoff._structured_conflicts()`.
    """
    positions = list(positions)
    if declared:
        return _declared_conflict(positions, threshold_pct, reason)
    if not positions:
        return {"status": SINGLE, "positions": [], "spread_pct": None,
                "likely_reason": None, "confidence_effect": None,
                "statement": "No sources to compare."}
    if len(positions) == 1:
        return {"status": SINGLE, "positions": [p.as_dict() for p in positions],
                "spread_pct": None, "likely_reason": None, "confidence_effect": None,
                "statement": "A single source; nothing to compare it against."}

    values = [_numeric(p.value) for p in positions]
    comparable = [v for v in values if v is not None and v != 0]

    spread = None
    if len(comparable) > 1:
        low, high = min(comparable), max(comparable)
        spread = (high - low) / abs(low) * 100.0

    if spread is None or spread <= threshold_pct:
        return {"status": AGREES, "positions": [p.as_dict() for p in positions],
                "spread_pct": spread, "likely_reason": None, "confidence_effect": None,
                "statement": ("Sources agree within %.1f%%." % spread
                              if spread is not None else
                              "Sources are not numerically comparable; no conflict "
                              "detected between them.")}

    return {
        "status": CONFLICTS,
        "positions": [p.as_dict() for p in positions],
        "spread_pct": spread,
        "likely_reason": _likely_reason(positions),
        # ADR-0009 and the research policy both require the confidence to drop rather than
        # the disagreement to be hidden.
        "confidence_effect": "lowered",
        "statement": ("Sources disagree by %.1f%%. Both figures are reported with their "
                      "source, date and definition; they are not averaged and neither is "
                      "silently preferred." % spread),
    }


def _spread_pct(positions):
    """Relative spread across the numerically comparable positions, or None."""
    values = [_numeric(p.value) for p in positions]
    comparable = [v for v in values if v is not None and v != 0]
    if len(comparable) < 2:
        return None
    low, high = min(comparable), max(comparable)
    return (high - low) / abs(low) * 100.0


def _declared_conflict(positions, threshold_pct, reason):
    """Record a disagreement the research layer observed and is reporting.

    The status is `CONFLICTS` whatever the numbers say. A declared conflict that the
    numeric test would have called agreement is the *interesting* case, not an error: it
    is how a definitional disagreement - the same metric measured two incompatible ways -
    reaches the evidence set at all.
    """
    spread = _spread_pct(positions)
    numerically = (AGREES if spread is None or spread <= threshold_pct else CONFLICTS)
    statement = ("Sources disagree. The disagreement was observed and reported by the "
                 "research layer; both positions are recorded with their source, date and "
                 "definition, and neither is averaged away nor silently preferred.")
    if spread is not None:
        statement += " They differ numerically by %.1f%%." % spread
    elif numerically == AGREES:
        statement += (" The positions are not numerically comparable, so the figures "
                      "alone would not have shown this.")
    return {
        "status": CONFLICTS,
        "declared": True,
        "positions": [p.as_dict() for p in positions],
        "spread_pct": spread,
        # Kept so a reader can see what the arithmetic alone would have concluded. It is
        # evidence about the conflict, never a vote on whether there is one.
        "numeric_assessment": numerically,
        "likely_reason": (str(reason).strip() if reason else _likely_reason(positions)),
        "confidence_effect": "lowered",
        "statement": statement,
    }


def _likely_reason(positions):
    """State a reason only when the positions themselves show one."""
    definitions = {p.definition for p in positions if p.definition}
    scopes = {p.scope for p in positions if p.scope}
    dates = {str(p.source_date)[:4] for p in positions if p.source_date}

    if len(definitions) > 1:
        return ("The sources use different definitions: %s."
                % "; ".join(sorted(definitions)))
    if len(scopes) > 1:
        return "The sources cover different scopes: %s." % "; ".join(sorted(scopes))
    if len(dates) > 1:
        return ("The sources are from different years (%s), so part of the gap may be "
                "real change rather than disagreement." % ", ".join(sorted(dates)))
    return None


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------
#
# A retrieved page must never choose its own tier. If it could, the cheapest prompt
# injection in the world would be a line reading "source tier: A" - and the whole point of
# tiering is that a content farm cannot promote itself. Tier is therefore assigned locally,
# from the source identity, by the tables below.

import re as _re

#: Domains and registry-controlled namespaces that identify a primary authoritative source.
#:
#: Every entry is matched at a **DNS label boundary** (`_matches_domain`), never as a
#: substring. A leading dot marks a namespace rather than a single host, but the matching
#: rule is identical: `gov` admits `sec.gov` and `www.sec.gov`, and refuses
#: `sec.gov.evil.example`, because the latter is a host in `evil.example`.
#:
#: **Removed in M9-C.6:** `eurostat`, `edgar`, `statistics` and `centralbank`. Those were
#: bare keyword fragments, not domains, and had no safe boundary reading - `statistics`
#: promoted any host containing the word, so `my-statistics-blog.example` scored tier A.
#: Nothing legitimate was lost: Eurostat is under `.europa.eu`, EDGAR under `sec.gov`, and
#: the national statistics offices under `.gov` / `.gov.uk`, all of which remain listed.
TIER_A_PATTERNS = (
    ".gov", ".gov.uk", ".mil", ".europa.eu", "ons.gov.uk", "sec.gov", "federalreserve.gov",
    "bankofengland.co.uk", "ecb.europa.eu", "imf.org", "worldbank.org", "oecd.org",
    "bls.gov", "census.gov", "companieshouse.gov.uk",
)

#: Established secondary sources: major business press, research houses, trade bodies.
#: Matched at a label boundary, so `ft.com` no longer promotes `microsoft.com` - the live
#: M9-C.5 defect - and `reuters.com` no longer promotes `fake-reuters.com`.
TIER_B_PATTERNS = (
    "reuters.com", "ft.com", "bloomberg.com", "wsj.com", "economist.com",
    "gartner.com", "forrester.com", "idc.com", "mckinsey.com", "bain.com",
    "deloitte.com", "pwc.com", "kpmg.com", "ey.com", "nielsen.com", "statista.com",
    "hbr.org", "ons.org", ".ac.uk", ".edu",
)

#: Companies whose **own** domains BusinessOps recognises as first-party sources, mapped to
#: the company name so a classification can explain itself. Added by M9-C.17; see ADR-0018.
#:
#: **Tier B, never tier A.** A company publishing about itself is primary and usually
#: accurate on facts only it holds - its own results, its own product launches - which is
#: what separates it from an unrecognised page and earns tier B: quotable with attribution
#: and date. It is not *independent*, which is what tier A means here (a regulator, a
#: statistical office, a central bank - a body with no stake in the number). Recognising
#: first-party sources therefore widens tier B and leaves tier A exactly as it was.
#:
#: **An explicit registry, never a heuristic.** There is no rule inferring first-party
#: status from a hostname: "any company `.com` is B" would hand a tier to anyone who can
#: register a domain, which is the M9-C.6 defect rebuilt with extra steps. An entry appears
#: here only by deliberate addition, and the table is code - retrieved content, a scout
#: reply and a caller all reach `classify_tier` far too late to add one.
#:
#: **Domains, not URL fragments**, matched by the same `_matches_domain` label-boundary
#: rule as every other table here. `microsoft.com` therefore admits `microsoft.com`,
#: `www.microsoft.com`, `news.microsoft.com`, `blogs.microsoft.com` and `ir.microsoft.com`,
#: and refuses `fake-microsoft.com`, `notmicrosoft.com`, `microsoft.com.evil.example` and
#: `microsoft.example.com`.
#:
#: **Deliberately tiny.** This is a policy mechanism, not a company-domain catalogue. The
#: one entry is the source M9-C.16's live verification found misclassified; entries are
#: added when a real retrieval shows one is needed, never speculatively.
FIRST_PARTY_COMPANY_DOMAINS = {
    "microsoft.com": "Microsoft Corporation",
}

#: The tier a registered first-party company domain receives. B, and the constant exists so
#: the policy is stated once rather than written into the classifier's control flow.
FIRST_PARTY_TIER = TIER_B

#: Shapes that mark a source as unattributable. Excluded outright.
TIER_D_PATTERNS = (
    "content-farm", "contentfarm", "ai-generated", "aigenerated", "scraped",
    "answers.", "ezinearticles", "articlesbase",
)

#: What an unrecognised source gets. Deliberately C, never A: an unknown domain may be
#: perfectly good, but it has not been shown to be, and "unrecognised" must never be
#: rewarded with authority. C means corroboration only, which is the safe reading.
UNRECOGNISED_TIER = TIER_C


def _host(reference):
    """The host portion of a URL, lowercased. No network access, no parsing library.

    Everything that could make two spellings of one host compare unequal is normalised
    here, so `_matches_domain` can be a plain boundary test: scheme, credentials, path,
    query, fragment, port and the optional root-zone trailing dot.
    """
    text = str(reference or "").strip().lower()
    text = _re.sub(r"^[a-z][a-z0-9+.-]*://", "", text)
    text = text.split("/")[0].split("?")[0].split("#")[0]
    # `user:pass@host` - the authority is what follows the last `@`, and a reference
    # written as `https://reuters.com@evil.example/` is a host in evil.example.
    text = text.rsplit("@", 1)[-1]
    if text.startswith("["):                       # IPv6 literal: [::1]:8080
        text = text.split("]")[0].lstrip("[")
    else:
        text = text.split(":")[0]                  # strip any port
    return text.rstrip(".")                        # `reuters.com.` is `reuters.com`


def _matches_domain(host, pattern):
    """True when `host` **is** the pattern's domain, or a subdomain of it.

    The whole of M9-C.6. The previous rule was `pattern in host`, which let any hostname
    containing a recognised domain inherit its tier: `microsoft.com` matched `ft.com`,
    `fake-reuters.com` matched `reuters.com`, and `sec.gov.evil.example` matched `.gov`.
    A tier is a trust statement, so substring containment was a self-promotion vector -
    anyone who can choose a hostname could choose a tier.

    Matching at a label boundary closes it. `reuters.com` admits `reuters.com` and
    `www.reuters.com`; it refuses `fake-reuters.com` (no dot before the domain),
    `notreuters.com` (likewise) and `reuters.com.evil.example` (a host in `evil.example`,
    which is what the rightmost labels always decide).

    A leading dot in a pattern reads as "this namespace", but needs no special case: after
    stripping it, the same rule gives `.gov` exactly the hosts that end in a `gov` label.
    """
    domain = pattern.lstrip(".")
    if not domain or not host:
        return False
    return host == domain or host.endswith("." + domain)


def classify_tier(reference, source=None):
    """Assign a source tier from the source identity alone.

    Returns `(tier, basis, inferred)`. `inferred` is True whenever the tier came from the
    fallback rather than from a recognised source, which callers use to decide whether a
    claim may rest on it: an inferred tier is a statement about our ignorance, not about
    the source's quality.

    Never consults retrieved content. A page cannot argue its way up a tier.
    """
    host = _host(reference)
    haystack = "%s %s" % (host, str(source or "").strip().lower())

    for pattern in TIER_D_PATTERNS:
        if pattern in haystack:
            return TIER_D, "matched excluded-source pattern %r" % pattern, False
    if not host:
        return UNRECOGNISED_TIER, "no resolvable source host; tier not established", True
    for pattern in TIER_A_PATTERNS:
        if _matches_domain(host, pattern):
            return TIER_A, "recognised primary authoritative source (%s)" % pattern, False
    for pattern in TIER_B_PATTERNS:
        if _matches_domain(host, pattern):
            return TIER_B, "recognised established secondary source (%s)" % pattern, False
    # First-party last among the recognised tables, so nothing here can raise a source that
    # already qualifies as authoritative or as established secondary press. It runs before
    # the fallback, which is the whole point: a company's own domain is *recognised*, not
    # unknown, and reporting it as unknown was the M9-C.16 gap.
    for domain in sorted(FIRST_PARTY_COMPANY_DOMAINS):
        if _matches_domain(host, domain):
            return (FIRST_PARTY_TIER,
                    "registered first-party company source (%s, %s); primary and "
                    "attributable, but not independent, so never tier A"
                    % (domain, FIRST_PARTY_COMPANY_DOMAINS[domain]), False)
    return (UNRECOGNISED_TIER,
            "source %r is not on the recognised A or B lists; classified C "
            "(corroboration only) rather than assumed authoritative" % host, True)
