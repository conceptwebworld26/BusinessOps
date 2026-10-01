"""M9-D.2 — the `/market-analysis` command.

The command is a markdown orchestrator: a model reads it as instructions. So what is
testable about it is its **contract** — that it is discoverable, that it declares the
inputs the skill accepts and refuses the ones it does not, that it delegates rather than
implements, and that no sentence in it can upgrade a result the skill produced.

Two things are deliberately *not* tested here:

  * **the dispatch leg.** A subagent is launched by the runtime, not by Python (ADR-0006,
    ADR-0014, ADR-0015). There is no transport to simulate, and inventing one would test a
    fiction. M9-D.2's live smoke test covers it, once, for real.
  * **the analysis itself.** That is `bops-market-analysis`, tested by
    `unit.test_m9d2_market_analysis`. A command test that re-asserted the skill's behaviour
    would be the duplication this command exists to avoid.

What *is* exercised against the real engine is the policy the command promises to preserve:
tier recomputation, candidate-claim status, conflict preservation and the fail-closed paths.
Those run through the same `open_retrieval`/`close_retrieval` calls the skill uses, with
fixtures standing in for the scout reply. No network access anywhere in this file.

This file follows `unit.test_m9d1_company_analysis_command` deliberately — same structure,
same collapsed-text convention, same separation of contract from pipeline — because the two
commands are the same shape and a reviewer should be able to read them side by side.
"""

import json
import os
import re
import unittest

from bops import commands
from bops import research as R
from bops.commands import registry
from bops.research import scout as scout_mod
from bops.research import sources as sources_mod

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_ID = "market-analysis"
COMMAND_MD = os.path.join(REPO, "commands", "%s.md" % COMMAND_ID)
SKILL = "bops-market-analysis"
SKILL_MD = os.path.join(REPO, "skills", SKILL, "SKILL.md")
COMPANY_COMMAND_MD = os.path.join(REPO, "commands", "company-analysis.md")

#: The five focus values the skill's input contract defines. The command may not invent a
#: sixth, and may not quietly drop one.
SUPPORTED_FOCUS = ("overview", "size-growth", "trends", "drivers-risks", "full")

MARKET = "cold chain logistics"
REQUEST = dict(subject=MARKET, category=R.MARKET, intent=R.OVERVIEW,
               public_terms={"geographic_market": "global", "period": "2026"},
               operation="m9d2-market-command-test")

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
               "warehousing, transport, packaging, monitoring and last-mile.",
    "claim_kind": "market_sizing"}

BLOG = {"source": "Freight Insider",
        "reference": "https://freightinsider.example/cold-chain-2026",
        "title": "Cold chain is booming", "publication_date": "2026-06-01",
        "source_type": "blog",
        "content": "Everyone says the cold chain market is about to double.",
        "claim_kind": "market_sizing"}


def read(path):
    """Text mode, so the repo's CRLF endings normalise before any regex or split."""
    return open(path, encoding="utf-8").read()


def body():
    """The command text with runs of whitespace collapsed.

    Markdown line wrapping is a formatting choice, not a contract: a sentence that happens
    to break after "executive" must read the same to a test as one that does not. Every
    prose assertion in this file therefore runs against the collapsed text, so rewrapping a
    paragraph can never fail a test and reflowing to dodge one can never pass it.
    """
    return re.sub(r"\s+", " ", read(COMMAND_MD))


def raw_lines():
    """The unmodified lines, for assertions about table rows."""
    return read(COMMAND_MD).split("\n")


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


def ingest(records, **overrides):
    request = dict(REQUEST)
    request.update(overrides)
    payload = reply(records, request["operation"])
    return R.close_retrieval(payload, request.pop("subject"), request.pop("category"),
                             **request)


def items_by_source(result):
    return {i["source"]: i for i in result["evidence"]["items"]}


# -- 59. Registration and discovery -----------------------------------------------------

class TestRegistration(unittest.TestCase):

    def test_59_the_command_exists(self):
        self.assertTrue(os.path.exists(COMMAND_MD), COMMAND_MD)

    def test_59a_the_command_name_is_exactly_market_analysis(self):
        self.assertEqual(os.path.basename(COMMAND_MD), "market-analysis.md")
        self.assertIn("# /market-analysis", body())

    def test_59b_it_is_discoverable_as_a_plugin_command(self):
        """Commands auto-discover from `commands/*.md` (architecture.md section 2).

        Discovery is the file being present with a parseable frontmatter block carrying a
        description — a command that loads with no description does not route at all.
        """
        found = [n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")]
        self.assertIn(COMMAND_ID, found)
        block = frontmatter(read(COMMAND_MD))
        self.assertTrue(re.search(r"^description:\s*\S", block, re.M))

    def test_59c_no_duplicate_registration(self):
        found = [n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")]
        self.assertEqual(found.count(COMMAND_ID), 1)

    def test_59d_it_carries_no_analytics_registry_spec(self):
        """It reads no dataset, so `commands.run()` must have nothing to run."""
        self.assertIsNone(registry.spec_for(COMMAND_ID))
        self.assertNotIn(COMMAND_ID, registry.COMMAND_IDS)
        self.assertNotIn("/%s" % COMMAND_ID, commands.catalogue_as_dict())

    def test_59e_running_it_through_the_analytics_runner_still_raises(self):
        with self.assertRaises(KeyError):
            registry.require(COMMAND_ID)

    def test_59f_frontmatter_declares_only_supported_fields(self):
        supported = {"description", "argument-hint", "allowed-tools",
                     "disable-model-invocation", "hide-from-slash-command-tool"}
        declared = set(re.findall(r"^([a-zA-Z-]+):", frontmatter(read(COMMAND_MD)), re.M))
        self.assertTrue(declared <= supported, declared - supported)

    def test_59g_frontmatter_is_single_line_per_field(self):
        """A wrapped description silently becomes a different YAML shape."""
        for line in frontmatter(read(COMMAND_MD)).split("\n"):
            self.assertFalse(line[:1] in (" ", "\t"), line[:40])

    def test_59h_the_argument_hint_names_the_five_focus_values(self):
        block = frontmatter(read(COMMAND_MD))
        hint = [l for l in block.split("\n") if l.startswith("argument-hint:")]
        self.assertTrue(hint)
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, hint[0], value)


# -- 60-64. Input reaches the skill -----------------------------------------------------

class TestInputContract(unittest.TestCase):

    def test_60_valid_input_is_routed_to_the_skill(self):
        text = body()
        self.assertIn("Invoke `%s`" % SKILL, text)
        self.assertIn("Pass it the market, the focus, the geography, the window and any "
                      "public terms", text)

    def test_60b_a_valid_market_is_accepted_by_the_engine_behind_it(self):
        out = R.open_retrieval(**REQUEST)
        self.assertEqual(out["status"], R.AUTHORISED)
        self.assertIn(MARKET, out["brief"]["query_text"])

    def test_61_market_is_declared_required(self):
        row = [l for l in raw_lines() if l.startswith("| market ")]
        self.assertTrue(row, "no market input row")
        self.assertIn("**yes**", row[0])

    def test_61b_a_missing_market_asks_and_does_not_retrieve(self):
        text = body().lower()
        self.assertIn("no market given", text)
        self.assertIn("do not choose a market", text)
        self.assertIn("do not retrieve", text)

    def test_62_an_unsupported_focus_is_rejected_rather_than_defaulted(self):
        text = body().lower()
        self.assertIn("unsupported `--focus`", text)
        self.assertIn("do not fall back to the default", text)

    def test_62b_every_supported_focus_value_is_named(self):
        text = body()
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, text, value)

    def test_62c_the_focus_values_match_the_skill_exactly(self):
        """The command may not invent a focus mode the skill cannot honour."""
        row = [l for l in read(SKILL_MD).split("\n") if l.startswith("| `focus`")]
        self.assertTrue(row, "skill declares no focus row")
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, row[0], value)

    def test_62d_competitor_comparison_is_not_offered_as_a_focus(self):
        row = [l for l in raw_lines() if l.startswith("| `--focus`")]
        self.assertTrue(row)
        self.assertNotIn("competitor", row[0].lower())

    def test_63_geography_is_declared_and_passed_through_unaltered(self):
        text = body()
        self.assertIn("--geography", text)
        self.assertIn("Passed to the skill **exactly** as given", text)
        self.assertIn("do not reinterpret a geography", text.lower())

    def test_63b_geography_reaches_the_query_through_the_engine(self):
        out = R.open_retrieval(**dict(REQUEST,
                                      public_terms={"geographic_market": "India"}))
        self.assertIn("India", out["brief"]["query_text"])

    def test_64_focus_and_the_other_optional_terms_are_passed_through(self):
        text = body()
        for flag in ("--focus", "--geography", "--industry", "--period", "--window"):
            self.assertIn(flag, text, flag)

    def test_64b_the_window_is_not_reinterpreted_by_the_command(self):
        text = body().lower()
        self.assertIn("passed through unread", text)
        self.assertIn("a scope parsed in two places is a scope with two meanings", text)

    def test_64c_business_context_precedence_is_not_bypassed(self):
        text = body().lower()
        self.assertIn("resolve business context", text)
        self.assertIn("do not guess it", text)

    def test_64d_business_context_may_contribute_public_terms_only(self):
        text = body()
        self.assertIn("**public** disambiguating terms", text)
        self.assertIn("nothing classified above `public` may", text.lower())

    def test_64e_ambiguity_routes_through_the_existing_protocol(self):
        text = body().lower()
        self.assertIn("ask which", text)
        self.assertIn("do not research a guess", text)
        self.assertIn("reference/ambiguity-protocol.md", text)

    def test_64f_it_does_not_invent_a_second_ambiguity_resolver(self):
        self.assertIn("do not resolve ambiguity here", body().lower())


# -- 65-68. The command implements nothing ----------------------------------------------

class TestThinOrchestration(unittest.TestCase):

    def test_65_it_declares_that_it_performs_no_research_step_itself(self):
        text = body().lower()
        self.assertIn("the command performs none of those steps itself", text)
        for verb in ("does not search", "tier a source", "build evidence",
                     "propose a claim", "verify one"):
            self.assertIn(verb, text, verb)

    def test_65b_it_contains_no_second_research_pipeline(self):
        """No gate call, no dispatch, no ingestion written into the command."""
        text = read(COMMAND_MD)
        for token in ("open_retrieval(", "close_retrieval(", "python -c",
                      "WebSearch", "WebFetch", "Task("):
            self.assertNotIn(token, text, token)

    def test_65c_it_dispatches_no_agent_of_its_own(self):
        self.assertNotIn("launch", body().lower())
        self.assertNotIn("dispatch **one**", body().lower())

    def test_65d_it_names_the_market_analysis_skill_as_its_implementation(self):
        self.assertIn(SKILL, body())
        self.assertIn("single source of analytical behaviour", body().lower())

    def test_65e_it_names_no_other_skill_as_its_implementation(self):
        """Strategy and competitor analysis are named only to refuse them."""
        named = set(re.findall(r"bops-[a-z-]+", body()))
        self.assertEqual(named - {SKILL, "bops-strategy-recommendations",
                                  "bops-competitor-analysis", "bops-research-scout"}, set())

    def test_66_it_constructs_no_evidence(self):
        text = read(COMMAND_MD)
        for token in ("EvidenceSet", "evidence_id", "BOPS-REC/1", "BOPS-END/1"):
            self.assertNotIn(token, text, token)

    def test_67_it_classifies_no_source(self):
        """Source policy lives in reference/ and the engine; a copy here is a placement bug."""
        text = read(COMMAND_MD)
        for token in ("TIER_A_PATTERNS", "TIER_B_PATTERNS", "FIRST_PARTY_COMPANY_DOMAINS",
                      "tier A or B source", "staleness window", "SOLE_SUPPORT_TIERS",
                      "STALENESS_DAYS"):
            self.assertNotIn(token, text, token)

    def test_68_it_creates_no_verified_claim(self):
        text = read(COMMAND_MD)
        self.assertIn("verified: false", text)
        self.assertNotIn("verified: true", text)
        self.assertNotIn("verified=true", text)

    def test_68b_it_restates_no_sizing_arithmetic(self):
        """The compatibility test and every calculation rule belong to the skill."""
        text = body()
        self.assertIn("No arithmetic here", text)
        self.assertIn("never averages estimates, never takes a midpoint, never converts "
                      "a currency and never derives a growth rate from two sizes", text)
        for token in ("CAGR =", "midpoint of", "/ 2", "compatibility test must hold"):
            self.assertNotIn(token, text, token)


# -- 69-72. Result propagation ----------------------------------------------------------

class TestResultPropagation(unittest.TestCase):

    #: The skill's fixed section order. The command reproduces, never redefines.
    SECTIONS = ("executive summary", "market definition and scope",
                "market size and growth", "key trends", "market drivers",
                "risks and constraints",
                "competitive/market structure observations", "evidence summary",
                "conflicts and limitations", "confidence")

    def section_list(self):
        """The one enumeration of all ten sections, isolated from the rest of the text.

        Searching the whole document would match `overview` in the argument hint and
        `confidence` in the prose, so the order assertion has to run against the list
        itself rather than against first-occurrence positions.
        """
        text = body().lower()
        start = text.index("its ten sections, in its order, unchanged")
        return text[start:text.index(".", text.index("confidence", start))]

    def test_69_the_skills_output_is_reproduced_rather_than_redefined(self):
        text = body().lower()
        self.assertIn("its ten sections, in its order, unchanged", text)
        self.assertIn("reproduced as it produced them", text)

    def test_70_all_ten_sections_are_preserved(self):
        listed = self.section_list()
        for section in self.SECTIONS:
            self.assertIn(section, listed, section)

    def test_70b_the_sections_appear_in_the_skills_order(self):
        listed = self.section_list()
        positions = [listed.index(s) for s in self.SECTIONS]
        self.assertEqual(positions, sorted(positions),
                         "command lists the sections out of the skill's order")

    def test_70c_the_order_matches_the_skills_own_numbered_table(self):
        """Read from the skill, so a reordering there fails here rather than drifting."""
        skill = read(SKILL_MD)
        start = skill.index("\n## Output\n")
        end = skill.index("\n## Failure conditions\n", start)
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", skill[start:end], re.M)
        ordered = [name.lower() for number, name in sorted(rows, key=lambda r: int(r[0]))]
        self.assertEqual(ordered, list(self.SECTIONS), ordered)

    def test_70d_a_section_with_no_evidence_is_not_padded(self):
        self.assertIn("A section with no evidence says so and is not padded", body())

    def test_71_limitations_and_confidence_are_not_footnotes(self):
        self.assertIn("never as a footnote", body().lower())

    def test_71b_candidate_status_is_preserved(self):
        self.assertIn("stays `candidate`", body().lower())

    def test_71c_unsupported_state_is_preserved(self):
        self.assertIn("stays unsupported", body().lower())

    def test_71d_a_declared_conflict_is_preserved(self):
        self.assertIn("a declared conflict stays a conflict", body().lower())

    def test_71e_a_source_forecast_stays_the_sources(self):
        self.assertIn("a source's forecast stays that source's estimate", body().lower())

    def test_71f_a_tier_c_source_is_not_promoted_by_the_command(self):
        self.assertIn("stays tier C", body())

    def test_71g_no_presentation_language_may_upgrade_a_result(self):
        text = body().lower()
        self.assertIn("nothing here may upgrade a result", text)
        self.assertIn("presentation changes wording, never status", text)

    def test_72_it_adds_no_recommendations(self):
        text = body().lower()
        self.assertIn("no recommendations", text)
        self.assertIn("bops-strategy-recommendations", text)
        self.assertNotIn("[recommendation]", text)

    def test_72b_it_produces_no_competitor_analysis(self):
        text = body().lower()
        self.assertIn("no competitor analysis", text)
        self.assertIn("bops-competitor-analysis", text)
        self.assertIn("section 7 is the shape of the market, not a list of rivals", text)


# -- Fail-closed ------------------------------------------------------------------------

class TestFailClosed(unittest.TestCase):

    def test_every_required_failure_condition_is_covered(self):
        text = body().lower()
        for condition in ("no market given", "malformed arguments", "unsupported `--focus`",
                          "market ambiguous", "not_authorised", "retrieval failed",
                          "no reliable source found", "only tier c", "sources conflict",
                          "scout reply malformed", "no adequate market-size source"):
            self.assertIn(condition, text, condition)

    def test_it_declares_fail_closed_explicitly(self):
        text = body().lower()
        self.assertIn("fail closed", text)
        self.assertIn("less output, never invented output", text)

    def test_a_failed_retrieval_is_never_filled_in(self):
        text = body().lower()
        self.assertIn("never filled in from the market name", text)
        self.assertIn("training knowledge", text)

    def test_a_malformed_scout_reply_is_not_repaired_or_retried(self):
        self.assertIn("do not repair, extract or re-dispatch", body().lower())

    def test_a_gate_refusal_is_not_rephrased(self):
        self.assertIn("never rephrase to get a different answer", body().lower())

    def test_ambiguity_triggers_no_retrieval(self):
        row = [l for l in raw_lines() if l.lower().startswith("| market ambiguous")]
        self.assertTrue(row)
        self.assertIn("No retrieval", row[0])

    def test_an_absent_size_is_stated_not_estimated(self):
        row = [l for l in raw_lines()
               if l.lower().startswith("| no adequate market-size source")]
        self.assertTrue(row)
        self.assertIn("Never estimate it", row[0])


# -- 73-74. Nothing else moved ----------------------------------------------------------

class TestNoRegression(unittest.TestCase):

    def test_73_the_company_analysis_command_is_unchanged(self):
        text = read(COMPANY_COMMAND_MD)
        self.assertIn("# /company-analysis", text)
        self.assertIn("bops-company-analysis", text)
        # Its own focus contract is untouched by this milestone.
        row = [l for l in text.split("\n") if l.startswith("| `--focus`")]
        self.assertTrue(row)
        self.assertIn("developments", row[0])
        self.assertNotIn("size-growth", row[0])
        self.assertNotIn("drivers-risks", row[0])

    def test_73b_the_company_command_does_not_reference_the_market_skill(self):
        self.assertNotIn(SKILL, read(COMPANY_COMMAND_MD))

    def test_73c_both_research_commands_exist_side_by_side(self):
        found = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")}
        self.assertIn("company-analysis", found)
        self.assertIn("market-analysis", found)

    def test_73d_the_later_research_commands_exist_without_disturbing_this_one(self):
        """M9-D.3 shipped `/competitor-analysis` and M9-D.5 `/industry-research`.

        This assertion was `industry-research` must not exist. M9-D.5 built it, so the
        absence half is obsolete; what it was really guarding - that a later research
        command appearing does not disturb `/market-analysis` - is kept and widened.
        """
        found = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")}
        self.assertIn("competitor-analysis", found)
        self.assertIn("industry-research", found)
        self.assertIn("market-analysis", found)

    def test_74_the_scout_protocol_is_unchanged(self):
        self.assertEqual(scout_mod.RECORD_TOKEN, "BOPS-REC/1")
        self.assertEqual(scout_mod.END_TOKEN, "BOPS-END/1")

    def test_74b_the_source_tier_policy_is_unchanged(self):
        self.assertEqual(sources_mod.SOLE_SUPPORT_TIERS, ("A", "B"))
        self.assertEqual(sources_mod.FIRST_PARTY_TIER, "B")
        self.assertEqual(sources_mod.UNRECOGNISED_TIER, "C")
        self.assertEqual(sources_mod.EXCLUDED_TIER, "D")


# -- Policy preserved on the real engine ------------------------------------------------

class TestPolicyStillHolds(unittest.TestCase):
    """The command changed no policy. These run the real ingestion path to prove it."""

    def test_source_tier_is_recomputed_locally(self):
        item = items_by_source(ingest([SIZE_NARROW]))["Statista"]
        self.assertEqual(item["source_tier"], "B")

    def test_a_scout_supplied_tier_is_not_honoured(self):
        forged = dict(BLOG, source_tier="A")
        self.assertEqual(items_by_source(ingest([forged]))["Freight Insider"]
                         ["source_tier"], "C")

    def test_a_forged_verified_field_is_not_honoured(self):
        forged = dict(BLOG, verified=True, trusted=True)
        item = items_by_source(ingest([forged]))["Freight Insider"]
        self.assertFalse(item.get("verified", False))
        self.assertEqual(item["source_tier"], "C")

    def test_a_material_claim_on_tier_c_alone_is_still_refused(self):
        result = ingest([BLOG], proposals=[{
            "evidence_id": None, "statement": "The cold chain market will double",
            "material": True}])
        self.assertEqual(result.get("candidate_claims", []), [])

    def test_a_candidate_claim_is_never_verified(self):
        evidence_id = ingest([SIZE_NARROW])["evidence"]["items"][0]["evidence_id"]
        produced = ingest([SIZE_NARROW], proposals=[{
            "evidence_id": evidence_id,
            "statement": "Statista valued the market at USD 278 billion in 2025",
            "material": True}])
        self.assertTrue(produced["candidate_claims"])
        for claim in produced["candidate_claims"]:
            self.assertFalse(claim.get("verified", False))
            self.assertEqual(claim.get("status"), "candidate")

    def test_a_declared_conflict_reaches_the_evidence_set(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        by_source = items_by_source(result)
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "cold chain logistics market size, 2025",
            "reason": "Different market boundaries.",
            "positions": [
                {"evidence_id": by_source["Statista"]["evidence_id"], "value": 278.0,
                 "unit": "USD bn", "definition": "warehousing and transport"},
                {"evidence_id": by_source["Gartner"]["evidence_id"], "value": 412.0,
                 "unit": "USD bn", "definition": "warehousing, transport, packaging"},
            ]}])
        self.assertEqual(declared["conflicts_not_recorded"], [])
        self.assertEqual(len(declared["evidence"]["conflicts"]), 1)
        self.assertEqual(declared["evidence"]["conflicts"][0]["confidence_effect"],
                         "lowered")

    def test_a_conflict_position_cannot_confer_a_tier(self):
        result = ingest([SIZE_NARROW, SIZE_BROAD])
        by_source = items_by_source(result)
        declared = ingest([SIZE_NARROW, SIZE_BROAD], conflicts=[{
            "subject": "market size",
            "positions": [
                {"evidence_id": by_source["Statista"]["evidence_id"], "value": 278.0,
                 "source_tier": "A"},
                {"evidence_id": by_source["Gartner"]["evidence_id"], "value": 412.0},
            ]}])
        self.assertTrue(declared["conflicts_not_recorded"])
        self.assertEqual(declared["evidence"]["conflicts"], [])

    def test_a_zero_record_reply_is_a_failed_retrieval_not_an_empty_analysis(self):
        self.assertNotEqual(ingest([]).get("status"), "ok")

    def test_a_reply_from_another_operation_yields_nothing(self):
        payload = reply([SIZE_NARROW], "some-other-operation")
        request = dict(REQUEST)
        result = R.close_retrieval(payload, request.pop("subject"),
                                   request.pop("category"), **request)
        self.assertNotEqual(result.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
