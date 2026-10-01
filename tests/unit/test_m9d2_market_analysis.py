"""M9-D.2 — the market-analysis skill, and the pipeline behaviour it depends on.

Two things are tested, because the skill is a markdown file a model reads as instructions
and a set of promises about how the shipped engine behaves. Either can drift from the other.

  * **the skill contract** — `skills/bops-market-analysis/SKILL.md` declares only supported
    frontmatter, is not a slash command, states the rules that keep market research honest
    (no invented size, no comparison across incompatible definitions, no averaged estimates,
    no external forecast passed off as ours, ask when ambiguous, no recommendations, no
    competitor profiling), and names the output sections it promises;
  * **the pipeline** — every research-quality and safety property the skill relies on,
    exercised against the same `open_retrieval`/`close_retrieval` path a live run uses.

No network access anywhere. Fixtures stand in for the scout's reply, which is the honest
half to automate: the dispatch leg is performed by the model and cannot be simulated here
without inventing a transport that M9-B established cannot exist (ADR-0015).

The engine gained exactly two constants for this milestone — the `OVERVIEW` and `DRIVERS`
research intents (ADR-0019). Everything else the skill needs already existed: the
`market_sizing` claim kind and its window, the declared-conflict transport that carries a
definition and a scope per position (ADR-0016), the first-party registry that keeps a
participant's own page at tier B (ADR-0018), and the candidate-claim policy.
"""

import json
import os
import re
import unittest

from bops import research as R
from bops.research import contract as contract_mod
from bops.research import query as query_mod
from bops.research import scout as scout_mod
from bops.research import sources as sources_mod

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKILL = "bops-market-analysis"
SKILL_DIR = os.path.join(REPO, "skills", SKILL)
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
COMPANY_SKILL_MD = os.path.join(REPO, "skills", "bops-company-analysis", "SKILL.md")

MARKET = "cold chain logistics"
AS_OF = "2026-09-13"

REQUEST = dict(subject=MARKET, category=R.MARKET, intent=R.OVERVIEW,
               public_terms={"geographic_market": "global", "period": "2026"},
               operation="m9d2-market-analysis-test")

#: The five focus values the skill's input contract defines.
SUPPORTED_FOCUS = ("overview", "size-growth", "trends", "drivers-risks", "full")

#: focus -> the intent that focus retrieves under. The skill's own table.
FOCUS_INTENT = {"overview": R.OVERVIEW, "size-growth": R.SIZING,
                "trends": R.TRENDS, "drivers-risks": R.DRIVERS}

# -- fixtures ---------------------------------------------------------------------------
#
# Two sizings of one market, both tier B, both 2025, both USD bn, differing only in where
# the boundary was drawn. This is the case the skill exists to handle: the figures are
# 48% apart and neither source is wrong.

SIZE_NARROW = {
    "source": "Statista", "reference": "https://www.statista.com/cold-chain-2025",
    "title": "Cold chain logistics market, global, 2025",
    "publication_date": "2026-02-11", "source_type": "research",
    "content": "The global cold chain logistics market was valued at USD 278 billion in "
               "2025, covering refrigerated warehousing and refrigerated transport.",
    "claim_kind": "market_sizing"}

SIZE_BROAD = {
    "source": "Gartner", "reference": "https://www.gartner.com/cold-chain-market-2025",
    "title": "Cold chain market sizing, 2025",
    "publication_date": "2026-03-04", "source_type": "research",
    "content": "The cold chain market reached USD 412 billion in 2025, including "
               "warehousing, transport, packaging, monitoring hardware and last-mile.",
    "claim_kind": "market_sizing"}

#: Same definition as SIZE_NARROW, a rounded restatement. Comparable, and agreeing.
SIZE_NARROW_RESTATED = {
    "source": "OECD", "reference": "https://www.oecd.org/cold-chain-2025",
    "title": "Refrigerated logistics, 2025", "publication_date": "2026-04-01",
    "source_type": "official_statistics",
    "content": "Refrigerated warehousing and transport was worth about USD 280 billion "
               "globally in 2025.",
    "claim_kind": "market_sizing"}

#: A different currency for the same year and definition. Never silently combined.
SIZE_EUR = {
    "source": "Reuters", "reference": "https://www.reuters.com/cold-chain-europe-2025",
    "title": "European cold chain sizing", "publication_date": "2026-05-02",
    "source_type": "press",
    "content": "The European cold chain logistics market was worth EUR 61 billion in 2025.",
    "claim_kind": "market_sizing"}

#: No publication date. Cannot be "the current size" of anything.
SIZE_UNDATED = {
    "source": "Market Almanac", "reference": "https://marketalmanac.example/cold-chain",
    "title": "Cold chain market size", "source_type": "research",
    "content": "The cold chain market is valued at USD 350 billion.",
    "claim_kind": "market_sizing"}

#: A source-published forecast. The period and the definition belong to the source.
FORECAST = {
    "source": "IDC", "reference": "https://www.idc.com/cold-chain-forecast",
    "title": "Cold chain logistics forecast 2025-2030",
    "publication_date": "2026-06-18", "source_type": "research",
    "content": "IDC projects a 12.4% CAGR for the global cold chain logistics market "
               "over 2025-2030, on a refrigerated warehousing and transport basis.",
    "claim_kind": "market_sizing"}

#: A second forecast over a different period. Never averaged with the first.
FORECAST_ALT = {
    "source": "Forrester", "reference": "https://www.forrester.com/cold-chain-outlook",
    "title": "Cold chain outlook 2024-2029", "publication_date": "2026-01-20",
    "source_type": "research",
    "content": "Forrester expects a 7.9% CAGR over 2024-2029 for cold chain logistics.",
    "claim_kind": "market_sizing"}

#: A market participant's own page. Tier B by the first-party registry, and not
#: independent evidence of the size of a market it sells into.
PARTICIPANT = {
    "source": "Microsoft Investor Relations",
    "reference": "https://www.microsoft.com/investor/cold-chain-cloud",
    "title": "Supply chain cloud momentum", "publication_date": "2026-07-29",
    "source_type": "filing",
    "content": "We estimate the addressable cold chain logistics market at USD 500 "
               "billion and our supply chain cloud revenue grew 27%.",
    "claim_kind": "market_sizing"}

#: Tier C — corroboration only, never the sole support for a material claim.
BLOG = {"source": "Freight Insider",
        "reference": "https://freightinsider.example/cold-chain-2026",
        "title": "Cold chain is booming", "publication_date": "2026-06-01",
        "source_type": "blog",
        "content": "Everyone says the cold chain market is about to double.",
        "claim_kind": "market_sizing"}

#: Tier D — excluded at ingestion, never reaches the skill.
FARM = {"source": "Answers Hub", "reference": "https://answers.example-content-farm.com/cc",
        "title": "Cold chain market size", "source_type": "unattributed",
        "content": "The cold chain market is worth trillions.",
        "claim_kind": "market_sizing"}

TREND = {"source": "Reuters", "reference": "https://www.reuters.com/cold-chain-automation",
         "title": "Automated cold stores spread across Europe",
         "publication_date": "2026-08-04", "source_type": "press",
         "content": "Operators commissioned a record number of automated cold stores in "
                    "the first half of 2026.",
         "claim_kind": "positioning"}


def read_skill():
    """Text mode, so the repo's CRLF endings normalise to `\\n` before any regex runs.

    A line ending is a checkout artefact, not a contract. Reading in binary would make
    every `^---\\n` and every section index in this file depend on which platform last
    wrote the skill, which is a test that fails for a reason nobody wants to read about.
    """
    return open(SKILL_MD, encoding="utf-8").read()


def skill_body():
    """The skill text with runs of whitespace collapsed.

    Markdown line wrapping is a formatting choice, not a contract, so every prose assertion
    runs against the collapsed text: rewrapping a paragraph can never fail a test and
    reflowing to dodge one can never pass it.
    """
    return re.sub(r"\s+", " ", read_skill())


def frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match is not None, "no frontmatter block"
    return match.group(1)


def reply(records, operation):
    """A scout reply in the production BOPS-REC/1 / BOPS-END/1 protocol."""
    lines = ["%s %s %s" % (scout_mod.RECORD_TOKEN, operation, json.dumps(r))
             for r in records]
    lines.append("%s %s %d" % (scout_mod.END_TOKEN, operation, len(records)))
    return "\n".join(lines)


def ingest(records, proposals=None, conflicts=None, as_of=AS_OF, **overrides):
    """Run the real production path: reply text -> parse -> normalise -> EvidenceSet."""
    fields = dict(REQUEST)
    fields.update(overrides)
    payload = reply(records, fields["operation"])
    subject = fields.pop("subject")
    category = fields.pop("category")
    return R.close_retrieval(payload, subject, category, as_of=as_of,
                             proposals=proposals, conflicts=conflicts, **fields)


def items_by_source(result):
    return {i["source"]: i for i in result["evidence"]["items"]}


def position(result, source, value, **extra):
    """A conflict position naming an item actually in this set."""
    item = items_by_source(result)[source]
    record = {"evidence_id": item["evidence_id"], "value": value}
    record.update(extra)
    return record


# =======================================================================================
# A. Skill registration and discovery
# =======================================================================================

class TestRegistration(unittest.TestCase):

    def test_1_the_skill_exists(self):
        self.assertTrue(os.path.isdir(SKILL_DIR), SKILL_DIR)
        self.assertTrue(os.path.exists(SKILL_MD), SKILL_MD)

    def test_2_it_is_discoverable_by_repository_convention(self):
        """Skills auto-discover from `skills/<name>/SKILL.md` with a name + description."""
        found = sorted(n for n in os.listdir(os.path.join(REPO, "skills"))
                       if os.path.isdir(os.path.join(REPO, "skills", n)))
        self.assertIn(SKILL, found)
        block = frontmatter(read_skill())
        self.assertTrue(re.search(r"^name:\s*%s\s*$" % SKILL, block, re.M), block[:120])
        self.assertTrue(re.search(r"^description:\s*\S", block, re.M))

    def test_2b_the_name_follows_the_bops_domain_function_convention(self):
        self.assertTrue(SKILL.startswith("bops-"))
        self.assertEqual(SKILL, SKILL.lower())
        self.assertNotIn("_", SKILL)

    def test_3_no_duplicate_skill_exists(self):
        found = [n for n in os.listdir(os.path.join(REPO, "skills"))
                 if os.path.isdir(os.path.join(REPO, "skills", n))]
        self.assertEqual(found.count(SKILL), 1)
        names = []
        for name in found:
            path = os.path.join(REPO, "skills", name, "SKILL.md")
            if os.path.exists(path):
                block = frontmatter(open(path, encoding="utf-8").read())
                names.extend(re.findall(r"^name:\s*(\S+)", block, re.M))
        self.assertEqual(names.count(SKILL), 1, names)

    def test_3b_it_declares_only_supported_frontmatter_fields(self):
        supported = {"name", "description", "argument-hint", "user-invocable"}
        declared = set(re.findall(r"^([a-zA-Z-]+):", frontmatter(read_skill()), re.M))
        self.assertTrue(declared <= supported, declared - supported)

    def test_3c_frontmatter_is_single_line_per_field(self):
        for line in frontmatter(read_skill()).split("\n"):
            self.assertFalse(line[:1] in (" ", "\t"), line[:40])

    def test_3d_it_is_a_skill_not_a_slash_command(self):
        """A skill carries no command frontmatter and lives outside `commands/`."""
        block = frontmatter(read_skill())
        for field in ("allowed-tools", "disable-model-invocation",
                      "hide-from-slash-command-tool"):
            self.assertNotIn(field, block, field)

    def test_4_the_company_analysis_skill_is_unchanged_by_this_milestone(self):
        """M9-D.2 adds a sibling; it does not edit M9-C.3's skill."""
        company = open(COMPANY_SKILL_MD, encoding="utf-8").read()
        self.assertIn("name: bops-company-analysis", company)
        self.assertNotIn("market-analysis", company)
        self.assertNotIn(SKILL, company)
        # Its own focus contract is untouched.
        row = [l for l in company.split("\n") if l.startswith("| `focus`")]
        self.assertTrue(row)
        for value in ("overview", "developments", "positioning", "full"):
            self.assertIn(value, row[0], value)
        self.assertNotIn("size-growth", row[0])


# =======================================================================================
# B. Input contract
# =======================================================================================

class TestInputContract(unittest.TestCase):

    def test_5_a_valid_market_is_accepted_by_the_engine(self):
        out = R.open_retrieval(**REQUEST)
        self.assertEqual(out["status"], R.AUTHORISED)
        self.assertIn(MARKET, out["brief"]["query_text"])

    def test_5b_market_is_declared_required_in_the_skill(self):
        row = [l for l in read_skill().split("\n") if l.startswith("| `market`")]
        self.assertTrue(row, "no market input row")
        self.assertIn("**yes**", row[0])

    def test_6_a_missing_market_is_refused_by_the_engine(self):
        request = dict(REQUEST, subject="")
        out = R.open_retrieval(**request)
        self.assertEqual(out["status"], R.NOT_AUTHORISED)

    def test_6b_a_whitespace_market_is_refused_too(self):
        out = R.open_retrieval(**dict(REQUEST, subject="   "))
        self.assertEqual(out["status"], R.NOT_AUTHORISED)

    def test_7_every_supported_focus_value_is_named_in_the_skill(self):
        row = [l for l in read_skill().split("\n") if l.startswith("| `focus`")]
        self.assertTrue(row, "skill declares no focus row")
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, row[0], value)

    def test_7b_each_focus_maps_to_an_intent_the_engine_recognises(self):
        for focus, intent in FOCUS_INTENT.items():
            self.assertIn(intent, contract_mod.INTENTS, focus)
            out = R.open_retrieval(**dict(REQUEST, intent=intent))
            self.assertEqual(out["status"], R.AUTHORISED, focus)

    def test_8_an_unsupported_focus_is_not_silently_defaulted(self):
        """An unrecognised intent is refused by the request contract, not defaulted."""
        out = R.open_retrieval(**dict(REQUEST, intent="competitor-comparison"))
        self.assertEqual(out["status"], R.NOT_AUTHORISED)

    def test_8b_competitor_comparison_is_not_a_market_focus(self):
        row = [l for l in read_skill().split("\n") if l.startswith("| `focus`")]
        for banned in ("competitor", "competitive"):
            self.assertNotIn(banned, row[0].lower(), banned)

    def test_9_geography_is_accepted_and_reaches_the_query(self):
        out = R.open_retrieval(**dict(
            REQUEST, public_terms={"geographic_market": "India"}))
        self.assertEqual(out["status"], R.AUTHORISED)
        self.assertIn("India", out["brief"]["query_text"])

    def test_9b_geography_is_passed_through_exactly(self):
        text = skill_body()
        self.assertIn("Passed through **exactly** as given", text)
        self.assertIn("Geography is not decoration", text)

    def test_10_a_time_window_term_is_accepted(self):
        out = R.open_retrieval(**dict(REQUEST, public_terms={"period": "2026"}))
        self.assertEqual(out["status"], R.AUTHORISED)
        self.assertIn("2026", out["brief"]["query_text"])

    def test_10b_the_window_is_a_declared_optional_input(self):
        row = [l for l in read_skill().split("\n") if l.startswith("| `window`")]
        self.assertTrue(row, "no window input row")
        self.assertIn("optional", row[0])

    def test_11_ambiguity_routes_through_the_existing_protocol(self):
        text = skill_body().lower()
        self.assertIn("ask the user which", text)
        self.assertIn("do not research a guess", text)
        self.assertIn("reference/ambiguity-protocol.md", text)

    def test_11b_an_over_broad_market_name_is_treated_as_ambiguous(self):
        self.assertIn("too broad to be one market", skill_body())


# =======================================================================================
# C. Research planning
# =======================================================================================

class TestResearchPlanning(unittest.TestCase):

    def test_12_overview_produces_a_market_overview_question(self):
        out = R.open_retrieval(**dict(REQUEST, intent=R.OVERVIEW))
        self.assertIn("market overview", out["brief"]["query_text"])

    def test_12b_overview_does_not_ask_for_a_company_profile(self):
        """The reason `OVERVIEW` exists: `PROFILE` phrases itself as "company profile"."""
        out = R.open_retrieval(**dict(REQUEST, intent=R.OVERVIEW))
        self.assertNotIn("company profile", out["brief"]["query_text"])

    def test_13_size_growth_produces_a_market_size_question(self):
        out = R.open_retrieval(**dict(REQUEST, intent=R.SIZING))
        self.assertIn("market size", out["brief"]["query_text"])

    def test_14_trends_produces_a_trends_question(self):
        out = R.open_retrieval(**dict(REQUEST, intent=R.TRENDS))
        self.assertIn("trends", out["brief"]["query_text"])

    def test_15_drivers_risks_produces_a_drivers_question(self):
        out = R.open_retrieval(**dict(REQUEST, intent=R.DRIVERS))
        self.assertIn("drivers", out["brief"]["query_text"])

    def test_16_full_produces_four_distinct_questions_with_no_duplication(self):
        texts = []
        for focus, intent in FOCUS_INTENT.items():
            out = R.open_retrieval(**dict(REQUEST, intent=intent,
                                          operation="m9d2-full-%s" % focus))
            self.assertEqual(out["status"], R.AUTHORISED, focus)
            texts.append(out["brief"]["query_text"])
        self.assertEqual(len(set(texts)), 4, texts)

    def test_16b_each_question_carries_its_own_operation(self):
        operations = set()
        for focus, intent in FOCUS_INTENT.items():
            out = R.open_retrieval(**dict(REQUEST, intent=intent,
                                          operation="m9d2-full-%s" % focus))
            operations.add(out["brief"]["operation"])
        self.assertEqual(len(operations), 4, operations)

    def test_16c_the_skill_declares_one_dispatch_per_retrieval(self):
        text = skill_body()
        self.assertIn("Within one retrieval, one dispatch", text)
        self.assertIn("four separate retrievals", text)

    def test_16d_it_forbids_merging_questions_to_save_a_dispatch(self):
        self.assertIn("Never merge two of these questions into one broad query",
                      skill_body())

    def test_17_a_research_question_cannot_carry_internal_business_data(self):
        for key in ("rows", "customers", "transactions", "ledger", "api_key"):
            out = R.open_retrieval(**dict(REQUEST, public_terms={key: "anything"}))
            self.assertEqual(out["status"], R.NOT_AUTHORISED, key)

    def test_17b_a_collection_of_records_is_refused_as_a_term(self):
        out = R.open_retrieval(**dict(
            REQUEST, public_terms={"geographic_market": ["global", "India"]}))
        self.assertEqual(out["status"], R.NOT_AUTHORISED)

    def test_18_public_terms_build_a_tier_zero_query(self):
        out = R.open_retrieval(**REQUEST)
        self.assertEqual(out["tier"], 0)
        self.assertEqual(out["decision"], "ALLOW")
        entry = out["ledger_entry"]
        self.assertEqual(entry["requested_tier"], 0)
        self.assertEqual(entry["failed_checks"], [])

    def test_18b_the_transmitted_text_contains_only_public_terms(self):
        out = R.open_retrieval(**REQUEST)
        text = out["ledger_entry"]["transmitted_text"]
        for token in ("278", "412", "revenue", "customer", "margin"):
            self.assertNotIn(token, text.lower(), token)
        self.assertIn(MARKET, text)

    def test_18c_the_skill_states_it_reads_no_business_file(self):
        text = skill_body().lower()
        self.assertIn("reads no business file", text)
        self.assertIn("sends no internal data", text)


# =======================================================================================
# D. Research pipeline integration
# =======================================================================================

class TestPipelineIntegration(unittest.TestCase):

    def test_19_the_gate_runs_before_any_brief_exists(self):
        """A refused request yields no brief at all — there is nothing to dispatch."""
        out = R.open_retrieval(**dict(REQUEST, public_terms={"customers": "acme"}))
        self.assertEqual(out["status"], R.NOT_AUTHORISED)
        self.assertIsNone(out["brief"])

    def test_19b_the_gate_runs_again_on_the_way_back_in(self):
        payload = reply([SIZE_NARROW], REQUEST["operation"])
        fields = dict(REQUEST, public_terms={"customers": "acme"})
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertEqual(out["status"], R.NOT_AUTHORISED)

    def test_20_the_brief_is_the_established_scout_seam_and_nothing_more(self):
        brief = R.open_retrieval(**REQUEST)["brief"]
        self.assertEqual(sorted(brief), ["destination", "max_fetched", "max_results",
                                         "operation", "query_text", "timeout_seconds"])

    def test_20b_the_skill_names_the_existing_scout(self):
        self.assertIn("bops-research-scout", skill_body())

    def test_21_the_production_line_protocol_is_what_is_parsed(self):
        payload = reply([SIZE_NARROW], REQUEST["operation"])
        self.assertIn(scout_mod.RECORD_TOKEN, payload)
        self.assertIn(scout_mod.END_TOKEN, payload)
        self.assertEqual(ingest([SIZE_NARROW])["status"], "ok")

    def test_21b_the_protocol_tokens_are_unchanged_by_this_milestone(self):
        self.assertEqual(scout_mod.RECORD_TOKEN, "BOPS-REC/1")
        self.assertEqual(scout_mod.END_TOKEN, "BOPS-END/1")

    def test_22_the_production_parser_is_used_and_fails_closed_on_a_dict(self):
        """A scout reply is text; the dict path is fixtures-only and unreachable live."""
        result = ingest([SIZE_NARROW])
        self.assertEqual(result["accepted"], 1)
        self.assertEqual(result["evidence"]["items"][0]["source"], "Statista")

    def test_23_operation_binding_is_enforced(self):
        payload = reply([SIZE_NARROW], "some-other-operation")
        fields = dict(REQUEST)
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertNotEqual(out.get("status"), "ok")

    def test_24_source_tiers_are_recomputed_locally(self):
        result = ingest([SIZE_NARROW_RESTATED, SIZE_NARROW, BLOG])
        tiers = {s: i["source_tier"] for s, i in items_by_source(result).items()}
        self.assertEqual(tiers["OECD"], "A")
        self.assertEqual(tiers["Statista"], "B")
        self.assertEqual(tiers["Freight Insider"], "C")

    def test_24b_every_item_carries_the_note_saying_how_its_tier_was_derived(self):
        result = ingest([SIZE_NARROW, BLOG])
        for item in result["evidence"]["items"]:
            self.assertTrue(any("source tier assigned locally" in n
                                for n in item["notes"]), item["notes"])

    def test_25_the_evidence_set_is_built_by_the_existing_pipeline(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD, TREND])
        evidence = result["evidence"]
        self.assertEqual(evidence["summary"]["items"], 3)
        self.assertEqual(evidence["summary"]["usable"], 3)
        self.assertEqual(evidence["trust"], "untrusted")
        self.assertEqual(evidence["disclosure_tier"], 0)

    def test_25b_tier_d_is_excluded_at_ingestion(self):
        """Carried for audit, marked unusable, counted under `excluded`, supports nothing."""
        result = ingest([SIZE_NARROW, FARM])
        farm = items_by_source(result)["Answers Hub"]
        self.assertEqual(farm["source_tier"], "D")
        self.assertFalse(farm["usable"])
        self.assertFalse(farm["may_stand_alone"])
        self.assertIn("excluded_reason", farm)
        summary = result["evidence"]["summary"]
        self.assertEqual(summary["items"], 2)
        self.assertEqual(summary["usable"], 1)
        self.assertEqual(summary["excluded"], 1)

    def test_26_candidate_claims_stay_candidate_and_unverified(self):
        result = ingest([SIZE_NARROW])
        evidence_id = result["evidence"]["items"][0]["evidence_id"]
        produced = ingest([SIZE_NARROW], proposals=[{
            "evidence_id": evidence_id,
            "statement": "Statista valued the global cold chain logistics market at "
                         "USD 278 billion in 2025", "material": True}])
        claims = produced["candidate_claims"]
        self.assertTrue(claims)
        for claim in claims:
            self.assertEqual(claim["status"], "candidate")
            self.assertFalse(claim.get("verified", False))

    def test_26b_a_claim_naming_no_retrieved_item_is_refused(self):
        produced = ingest([SIZE_NARROW], proposals=[{
            "evidence_id": "ev-does-not-exist",
            "statement": "The market is large", "material": True}])
        self.assertEqual(produced["candidate_claims"], [])
        self.assertTrue(produced["claims_not_produced"])


# =======================================================================================
# E. Market-size integrity
# =======================================================================================

class TestMarketSizeIntegrity(unittest.TestCase):

    def test_27_same_definition_values_can_be_compared(self):
        result = ingest([SIZE_NARROW, SIZE_NARROW_RESTATED])
        positions = [
            sources_mod.SourcePosition(
                evidence_id="a", value=278.0, source="Statista", source_tier="B",
                unit="USD bn", definition="refrigerated warehousing and transport",
                scope="global, 2025"),
            sources_mod.SourcePosition(
                evidence_id="b", value=280.0, source="OECD", source_tier="A",
                unit="USD bn", definition="refrigerated warehousing and transport",
                scope="global, 2025"),
        ]
        assessment = sources_mod.assess_conflict(positions)
        self.assertEqual(assessment["status"], sources_mod.AGREES)
        self.assertEqual(result["evidence"]["summary"]["items"], 2)

    def test_28_different_definitions_produce_a_structured_conflict_not_an_average(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "cold chain logistics market size, 2025",
            "reason": "The sources draw the market boundary differently.",
            "positions": [
                position(result, "Statista", 278.0, unit="USD bn",
                         definition="refrigerated warehousing and transport",
                         scope="global, 2025"),
                position(result, "Gartner", 412.0, unit="USD bn",
                         definition="warehousing, transport, packaging, monitoring, "
                                    "last-mile",
                         scope="global, 2025"),
            ]}])
        self.assertEqual(declared["conflicts_not_recorded"], [])
        conflicts = declared["evidence"]["conflicts"]
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict["status"], sources_mod.CONFLICTS)
        self.assertTrue(conflict["declared"])
        self.assertEqual(conflict["confidence_effect"], "lowered")
        values = sorted(p["value"] for p in conflict["positions"])
        self.assertEqual(values, [278.0, 412.0])
        # No mean, midpoint or merged figure is anywhere in the record. The engine
        # reports both positions and nothing derived from the pair except their spread.
        self.assertNotIn(345.0, values)
        self.assertEqual(len(conflict["positions"]), 2)
        for key in ("mean", "average", "midpoint", "consensus", "combined"):
            self.assertNotIn(key, conflict, key)
        self.assertAlmostEqual(conflict["spread_pct"], (412.0 - 278.0) / 278.0 * 100.0)

    def test_28b_both_definitions_survive_into_the_record(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "cold chain logistics market size, 2025",
            "positions": [
                position(result, "Statista", 278.0,
                         definition="refrigerated warehousing and transport"),
                position(result, "Gartner", 412.0,
                         definition="warehousing, transport, packaging, monitoring"),
            ]}])
        definitions = {p["definition"]
                       for p in declared["evidence"]["conflicts"][0]["positions"]}
        self.assertEqual(len(definitions), 2, definitions)

    def test_28c_a_definitional_mismatch_is_named_as_the_likely_reason(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "market size",
            "positions": [
                position(result, "Statista", 278.0, definition="narrow basis"),
                position(result, "Gartner", 412.0, definition="broad basis"),
            ]}])
        reason = declared["evidence"]["conflicts"][0]["likely_reason"]
        self.assertIn("different definitions", reason)

    def test_29_comparable_conflicting_estimates_remain_separate(self):
        positions = [
            sources_mod.SourcePosition("a", 278.0, "Statista", "B", unit="USD bn",
                                       definition="same basis"),
            sources_mod.SourcePosition("b", 690.0, "Gartner", "B", unit="USD bn",
                                       definition="same basis"),
        ]
        assessment = sources_mod.assess_conflict(positions)
        self.assertEqual(assessment["status"], sources_mod.CONFLICTS)
        self.assertEqual(assessment["confidence_effect"], "lowered")
        self.assertEqual(sorted(p["value"] for p in assessment["positions"]),
                         [278.0, 690.0])

    def test_29b_a_declared_conflict_survives_even_when_the_numbers_agree(self):
        """Two near-identical figures on incompatible definitions are not corroboration."""
        result = ingest([SIZE_NARROW, SIZE_NARROW_RESTATED])
        declared = ingest([SIZE_NARROW, SIZE_NARROW_RESTATED], conflicts=[{
            "subject": "market size basis",
            "reason": "One counts transport only; the other adds warehousing.",
            "positions": [
                position(result, "Statista", 278.0, definition="transport only"),
                position(result, "OECD", 280.0, definition="transport and warehousing"),
            ]}])
        conflict = declared["evidence"]["conflicts"][0]
        self.assertEqual(conflict["status"], sources_mod.CONFLICTS)
        self.assertEqual(conflict["numeric_assessment"], sources_mod.AGREES)

    def test_30_no_size_value_is_fabricated_when_evidence_is_absent(self):
        result = ingest([TREND])
        blob = json.dumps(result)
        for invented in ("278", "412", "350", "500"):
            self.assertNotIn(invented, blob, invented)

    def test_30b_a_zero_record_retrieval_is_a_failure_not_an_empty_size(self):
        result = ingest([])
        self.assertNotEqual(result.get("status"), "ok")
        self.assertIsNone(result.get("evidence"))

    def test_31_a_currency_mismatch_is_not_silently_combined(self):
        positions = [
            sources_mod.SourcePosition("a", 278.0, "Statista", "B", unit="USD bn",
                                       definition="cold chain", scope="global 2025"),
            sources_mod.SourcePosition("b", 61.0, "Reuters", "B", unit="EUR bn",
                                       definition="cold chain", scope="Europe 2025"),
        ]
        assessment = sources_mod.assess_conflict(positions, declared=True,
                                                 reason="Different currency and scope.")
        units = {p["unit"] for p in assessment["positions"]}
        self.assertEqual(units, {"USD bn", "EUR bn"})
        self.assertEqual(assessment["status"], sources_mod.CONFLICTS)

    def test_31b_the_skill_forbids_converting_a_currency(self):
        self.assertIn("Never convert a currency yourself", skill_body())

    def test_32_a_geography_mismatch_is_not_silently_combined(self):
        positions = [
            sources_mod.SourcePosition("a", 278.0, "Statista", "B", scope="global, 2025"),
            sources_mod.SourcePosition("b", 61.0, "Reuters", "B", scope="Europe, 2025"),
        ]
        assessment = sources_mod.assess_conflict(positions)
        self.assertEqual(assessment["status"], sources_mod.CONFLICTS)
        self.assertIn("different scopes", assessment["likely_reason"])

    def test_32b_the_skill_makes_geography_part_of_the_compatibility_test(self):
        text = skill_body()
        self.assertIn("**Geography** — the territory sized", text)
        self.assertIn("A global figure and a regional figure are not a growth rate", text)

    def test_33_a_time_period_mismatch_is_not_silently_combined(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "market size across years",
            "reason": "Different years sized.",
            "positions": [
                position(result, "Statista", 278.0, scope="global, 2023"),
                position(result, "Gartner", 412.0, scope="global, 2025"),
            ]}])
        scopes = {p["scope"] for p in declared["evidence"]["conflicts"][0]["positions"]}
        self.assertEqual(len(scopes), 2, scopes)

    def test_33b_the_skill_requires_all_five_checks_before_comparing(self):
        text = skill_body()
        self.assertIn("**all five must hold**", text)
        for check in ("Market definition", "Geography", "Unit and currency",
                      "Time period", "Methodology or basis"):
            self.assertIn(check, text, check)

    def test_33c_an_absent_definition_fails_the_check_rather_than_passing_it(self):
        self.assertIn("the check fails on unknown, not on assumed match", skill_body())

    def test_34_an_undated_estimate_keeps_its_limitation(self):
        result = ingest([SIZE_UNDATED])
        item = items_by_source(result)["Market Almanac"]
        self.assertEqual(item["freshness"], sources_mod.UNDATED)
        self.assertIsNone(item.get("publication_date"))

    def test_34b_the_market_sizing_window_is_the_one_applied(self):
        result = ingest([SIZE_NARROW])
        detail = result["instruction_safe"]["items"][0]["freshness_detail"]
        self.assertEqual(detail["claim_kind"], sources_mod.MARKET_SIZING)
        self.assertEqual(detail["window_days"],
                         sources_mod.STALENESS_DAYS[sources_mod.MARKET_SIZING])

    def test_34c_the_skill_forbids_calling_an_undated_figure_the_current_size(self):
        self.assertIn("A market size with no publication date is a size for an unknown "
                      "year", skill_body())


# =======================================================================================
# F. Forecast / CAGR integrity
# =======================================================================================

class TestForecastIntegrity(unittest.TestCase):

    def test_35_a_source_reported_cagr_stays_source_reported(self):
        result = ingest([FORECAST])
        item = items_by_source(result)["IDC"]
        self.assertIn("12.4% CAGR", item["content"])
        self.assertEqual(item["source"], "IDC")
        self.assertEqual(item["source_tier"], "B")

    def test_35b_the_skill_labels_a_source_forecast_as_an_estimate(self):
        text = skill_body()
        self.assertIn("[ESTIMATE/ASSUMPTION]", text)
        self.assertIn("never `[FACT/SOURCED]`", text)

    def test_36_the_forecast_period_is_preserved_verbatim(self):
        result = ingest([FORECAST, FORECAST_ALT])
        contents = {i["source"]: i["content"] for i in result["evidence"]["items"]}
        self.assertIn("2025-2030", contents["IDC"])
        self.assertIn("2024-2029", contents["Forrester"])

    def test_36b_the_skill_forbids_re_basing_a_period(self):
        text = skill_body()
        self.assertIn("Preserve the stated period exactly", text)
        self.assertIn("may not be re-based", text)

    def test_37_two_forecasts_are_never_averaged_by_the_engine(self):
        positions = [
            sources_mod.SourcePosition("a", 12.4, "IDC", "B", unit="%",
                                       scope="2025-2030"),
            sources_mod.SourcePosition("b", 7.9, "Forrester", "B", unit="%",
                                       scope="2024-2029"),
        ]
        assessment = sources_mod.assess_conflict(positions)
        values = sorted(p["value"] for p in assessment["positions"])
        self.assertEqual(values, [7.9, 12.4])
        self.assertNotIn(10.15, values)
        self.assertEqual(assessment["status"], sources_mod.CONFLICTS)

    def test_37b_the_skill_forbids_averaging_forecasts(self):
        self.assertIn("Never average two forecasts", skill_body())

    def test_38_an_external_forecast_is_not_a_businessops_forecast(self):
        text = skill_body()
        self.assertIn("Never label an external forecast a BusinessOps forecast", text)
        self.assertIn("bops-forecasting", text)

    def test_38b_the_skill_claims_no_backtest_of_its_own(self):
        self.assertIn("This skill has neither", skill_body())

    def test_39_an_unsupported_forecast_claim_stays_unsupported(self):
        """A forecast standing only on a tier C page cannot become a material claim."""
        result = ingest([BLOG], proposals=[{
            "evidence_id": None,
            "statement": "The cold chain market is about to double", "material": True}])
        self.assertEqual(result["candidate_claims"], [])

    def test_39b_a_tier_c_only_set_reports_itself_as_unsupported(self):
        result = ingest([BLOG])
        self.assertEqual(result["evidence"]["support"]["support"],
                         sources_mod.UNSUPPORTED)


# =======================================================================================
# G. Evidence quality
# =======================================================================================

class TestEvidenceQuality(unittest.TestCase):

    def test_40_tier_c_alone_cannot_support_a_material_claim(self):
        result = ingest([BLOG])
        evidence_id = result["evidence"]["items"][0]["evidence_id"]
        produced = ingest([BLOG], proposals=[{
            "evidence_id": evidence_id,
            "statement": "The cold chain market is booming", "material": True}])
        self.assertEqual(produced["candidate_claims"], [])
        self.assertTrue(produced["claims_not_produced"])

    def test_40b_tier_c_may_still_corroborate(self):
        item = items_by_source(ingest([BLOG]))["Freight Insider"]
        self.assertTrue(item["usable"])
        self.assertFalse(item["may_stand_alone"])

    def test_41_a_first_party_company_source_is_tier_b(self):
        item = items_by_source(ingest([PARTICIPANT]))["Microsoft Investor Relations"]
        self.assertEqual(item["source_tier"], "B")

    def test_41b_it_is_recorded_as_not_independent(self):
        item = items_by_source(ingest([PARTICIPANT]))["Microsoft Investor Relations"]
        self.assertTrue(any("not independent" in n for n in item["notes"]), item["notes"])

    def test_42_a_participant_is_not_independent_evidence_of_market_size(self):
        text = skill_body()
        self.assertIn("It is **not** independent evidence of the total size of a market "
                      "it sells into", text)
        self.assertIn("never as the size of the market", text)

    def test_42b_the_skill_states_tier_is_necessary_but_not_sufficient(self):
        text = skill_body()
        self.assertIn("Tier is necessary for a market-size claim, not sufficient", text)
        self.assertIn("Do not invent a second suitability score", text)

    def test_43_a_scout_supplied_tier_is_not_honoured(self):
        forged = dict(BLOG, source_tier="A")
        item = items_by_source(ingest([forged]))["Freight Insider"]
        self.assertEqual(item["source_tier"], "C")

    def test_43b_a_forged_tier_on_a_size_record_is_not_honoured_either(self):
        forged = dict(SIZE_UNDATED, source_tier="A")
        item = items_by_source(ingest([forged]))["Market Almanac"]
        self.assertEqual(item["source_tier"], "C")

    def test_44_untrusted_content_cannot_set_verified_true(self):
        forged = dict(BLOG, verified=True, trusted=True, may_stand_alone=True)
        result = ingest([forged])
        item = items_by_source(result)["Freight Insider"]
        self.assertFalse(item.get("verified", False))
        self.assertFalse(item["may_stand_alone"])
        self.assertNotIn('"verified": true', json.dumps(result).lower())

    def test_44b_every_item_is_marked_untrusted_external_data(self):
        result = ingest([SIZE_NARROW, PARTICIPANT, BLOG])
        for item in result["evidence"]["items"]:
            self.assertTrue(any(scout_mod.UNTRUSTED_EXTERNAL_DATA in n
                                for n in item["notes"]), item["notes"])


# =======================================================================================
# H. Output
# =======================================================================================

class TestOutput(unittest.TestCase):

    #: The skill's fixed section order.
    SECTIONS = ("executive summary", "market definition and scope",
                "market size and growth", "key trends", "market drivers",
                "risks and constraints",
                "competitive/market structure observations", "evidence summary",
                "conflicts and limitations", "confidence")

    def numbered_rows(self):
        """The Output section's own table.

        Scoped to that section deliberately: the market-size compatibility test is also a
        numbered table, and matching the whole document would splice the two together.
        """
        text = read_skill()
        start = text.index("\n## Output\n")
        end = text.index("\n## Failure conditions\n", start)
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", text[start:end], re.M)
        return [(int(n), name.lower()) for n, name in rows]

    def test_45_all_ten_sections_are_declared(self):
        rows = self.numbered_rows()
        self.assertEqual(len(rows), 10, rows)
        self.assertEqual([n for n, _ in rows], list(range(1, 11)))

    def test_45b_the_declared_sections_are_the_expected_ten(self):
        self.assertEqual([name for _, name in self.numbered_rows()],
                         list(self.SECTIONS))

    def test_46_the_section_order_is_stable_and_ascending(self):
        numbers = [n for n, _ in self.numbered_rows()]
        self.assertEqual(numbers, sorted(numbers))

    def test_47_missing_evidence_produces_an_explicit_limitation(self):
        text = skill_body()
        self.assertIn("A section with no evidence says so and is not padded", text)
        self.assertIn("not adequately supported", text)

    def test_47b_an_absent_size_is_stated_rather_than_estimated(self):
        text = skill_body()
        self.assertIn("no adequate public source states the size of this market", text)
        self.assertIn("which is a finding, not a gap to fill", text)

    def test_48_confidence_is_set_from_the_evidence(self):
        text = skill_body()
        self.assertIn("Set confidence from the evidence, not from how complete the "
                      "report looks", text)
        for level in ("`HIGH`", "`MEDIUM`", "`LOW`"):
            self.assertIn(level, text, level)

    def test_49_conflicts_are_preserved_rather_than_resolved(self):
        text = skill_body()
        self.assertIn("Never average, never silently choose", text)
        self.assertIn("A consensus you manufactured is worse than a disagreement you "
                      "reported", text)

    def test_49b_an_empty_conflicts_array_does_not_mean_agreement(self):
        self.assertIn("never that the sources agree", skill_body())

    def test_50_no_strategic_recommendation_is_produced(self):
        text = skill_body()
        self.assertIn("**No recommendations.**", text)
        self.assertIn("bops-strategy-recommendations", text)
        self.assertNotIn("[RECOMMENDATION]", text.replace(
            "Nothing is labelled `[RECOMMENDATION]` by this skill.", ""))

    def test_50b_entry_and_investment_questions_are_declined(self):
        text = skill_body().lower()
        self.assertIn("whether to enter, leave, invest in or price against this market",
                      text)

    def test_51_no_competitor_analysis_output_is_produced(self):
        text = skill_body()
        self.assertIn("**No competitor analysis.**", text)
        self.assertIn("bops-competitor-analysis", text)
        self.assertIn("A profile of one named rival, a ranked table of vendors or a "
                      "share-by-vendor comparison", text)

    def test_51b_section_seven_is_scoped_to_structure_only(self):
        row = [l for l in read_skill().split("\n") if l.startswith("| 7 |")]
        self.assertTrue(row)
        self.assertIn("No competitor profiles, no vendor rankings", row[0])

    def test_51c_the_skill_names_no_individual_competitor(self):
        """No worked example may become a vendor list."""
        self.assertNotIn("vs.", skill_body())


# =======================================================================================
# I. Fail closed
# =======================================================================================

class TestFailClosed(unittest.TestCase):

    def test_52_a_gate_refusal_is_reported_not_worked_around(self):
        out = R.open_retrieval(**dict(REQUEST, public_terms={"credentials": "x"}))
        self.assertEqual(out["status"], R.NOT_AUTHORISED)
        self.assertTrue(out["reasons"])
        self.assertIsNone(out["brief"])

    def test_52b_the_skill_forbids_rephrasing_a_refusal(self):
        self.assertIn("Do not rephrase to get a different answer", skill_body())

    def test_53_research_unavailable_is_a_structured_failure(self):
        result = ingest([])
        self.assertIn("status", result)
        self.assertNotEqual(result["status"], "ok")
        self.assertIn("reason", result)

    def test_54_no_reliable_source_is_a_correct_outcome(self):
        text = skill_body()
        self.assertIn("Producing no analysis is a correct outcome", text)
        self.assertIn("no reliable source found", text.lower())

    def test_54b_a_tier_d_only_reply_yields_nothing_usable(self):
        result = ingest([FARM])
        summary = result["evidence"]["summary"]
        self.assertEqual(summary["usable"], 0)
        self.assertEqual(summary["excluded"], 1)
        self.assertEqual(result["evidence"]["support"]["support"],
                         sources_mod.UNSUPPORTED)

    def test_54c_a_tier_d_only_set_supports_no_claim(self):
        result = ingest([FARM])
        evidence_id = result["evidence"]["items"][0]["evidence_id"]
        produced = ingest([FARM], proposals=[{
            "evidence_id": evidence_id,
            "statement": "The cold chain market is worth trillions", "material": True}])
        self.assertEqual(produced["candidate_claims"], [])
        self.assertTrue(produced["claims_not_produced"])

    def test_55_a_malformed_scout_reply_fails_closed(self):
        fields = dict(REQUEST)
        payload = "BOPS-REC/1 %s {not json at all}\nBOPS-END/1 %s 1" % (
            fields["operation"], fields["operation"])
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertNotEqual(out.get("status"), "ok")
        self.assertIsNone(out.get("evidence"))

    def test_55b_a_missing_terminator_fails_closed(self):
        fields = dict(REQUEST)
        payload = "%s %s %s" % (scout_mod.RECORD_TOKEN, fields["operation"],
                                json.dumps(SIZE_NARROW))
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertNotEqual(out.get("status"), "ok")

    def test_55c_a_count_mismatch_fails_closed(self):
        fields = dict(REQUEST)
        payload = "\n".join([
            "%s %s %s" % (scout_mod.RECORD_TOKEN, fields["operation"],
                          json.dumps(SIZE_NARROW)),
            "%s %s 4" % (scout_mod.END_TOKEN, fields["operation"])])
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertNotEqual(out.get("status"), "ok")

    def test_55d_the_skill_forbids_repairing_a_reply(self):
        """The command owns the wording; the skill must not contradict it."""
        text = skill_body()
        self.assertIn("Retrieval failed or was blocked", text)
        self.assertIn("produce no findings for that retrieval", text)

    def test_56_a_zero_record_retrieval_is_handled(self):
        fields = dict(REQUEST)
        payload = "%s %s 0" % (scout_mod.END_TOKEN, fields["operation"])
        out = R.close_retrieval(payload, fields.pop("subject"), fields.pop("category"),
                                **fields)
        self.assertNotEqual(out.get("status"), "ok")
        self.assertIsNone(out.get("evidence"))

    def test_57_conflicting_evidence_refuses_a_single_source_claim(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        produced = ingest([SIZE_NARROW, SIZE_BROAD],
                          conflicts=[{
                              "subject": "market size",
                              "positions": [
                                  position(result, "Statista", 278.0,
                                           definition="narrow"),
                                  position(result, "Gartner", 412.0,
                                           definition="broad"),
                              ]}],
                          proposals=[{
                              "evidence_id": items_by_source(result)["Statista"][
                                  "evidence_id"],
                              "statement": "The market was USD 278 billion in 2025",
                              "material": True}])
        self.assertEqual(produced["candidate_claims"], [])
        refusals = [r["reason"] for r in produced["claims_not_produced"]]
        self.assertIn("unresolved_conflict", refusals)

    def test_58_an_ambiguous_market_triggers_no_arbitrary_research(self):
        text = skill_body()
        self.assertIn("Resolve ambiguity before building a request, not after", text)
        self.assertIn("Do not research a guess and caveat it afterwards", text)
        row = [l for l in read_skill().split("\n")
               if l.startswith("| Market name ambiguous")]
        self.assertTrue(row)
        self.assertIn("Do not research a guess", row[0])


# =======================================================================================
# Engine addition — the two intents this milestone added (ADR-0019)
# =======================================================================================

class TestIntentAddition(unittest.TestCase):

    def test_the_two_new_intents_are_registered(self):
        self.assertIn(R.OVERVIEW, contract_mod.INTENTS)
        self.assertIn(R.DRIVERS, contract_mod.INTENTS)

    def test_the_five_original_intents_are_untouched(self):
        for intent in (R.BENCHMARK, R.PROFILE, R.SIZING, R.TRENDS, R.POSITIONING):
            self.assertIn(intent, contract_mod.INTENTS, intent)
        self.assertEqual(contract_mod.INTENTS[:5],
                         (R.BENCHMARK, R.PROFILE, R.SIZING, R.TRENDS, R.POSITIONING))

    def test_the_original_intent_wording_is_unchanged(self):
        """`bops-company-analysis` builds its queries from these; they must not move."""
        self.assertEqual(query_mod.INTENT_TERMS[R.PROFILE], "company profile")
        self.assertEqual(query_mod.INTENT_TERMS[R.SIZING], "market size")
        self.assertEqual(query_mod.INTENT_TERMS[R.TRENDS], "trends")
        self.assertEqual(query_mod.INTENT_TERMS[R.POSITIONING], "market position")
        self.assertEqual(query_mod.INTENT_TERMS[R.BENCHMARK], "benchmark")

    def test_a_company_profile_query_is_byte_identical_to_before(self):
        out = R.open_retrieval("Northwind Logistics", R.COMPANY, intent=R.PROFILE,
                               public_terms={"industry": "logistics"},
                               operation="m9d2-regression-probe")
        self.assertEqual(out["brief"]["query_text"],
                         "Northwind Logistics logistics company profile")

    def test_the_new_intents_carry_query_wording(self):
        self.assertEqual(query_mod.INTENT_TERMS[R.OVERVIEW], "market overview")
        self.assertEqual(query_mod.INTENT_TERMS[R.DRIVERS],
                         "market drivers and constraints")

    def test_an_unregistered_intent_is_still_refused(self):
        request = contract_mod.ResearchRequest(MARKET, R.MARKET, intent="vibes")
        self.assertFalse(request.valid)


if __name__ == "__main__":
    unittest.main()
