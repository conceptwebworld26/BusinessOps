"""M9-D.1 — the `/company-analysis` command.

The command is a markdown orchestrator: a model reads it as instructions. So what is
testable about it is its **contract** — that it is discoverable, that it declares the
inputs the skill accepts and refuses the ones it does not, that it delegates rather than
implements, and that no sentence in it can upgrade a result the skill produced.

Two things are deliberately *not* tested here:

  * **the dispatch leg.** A subagent is launched by the runtime, not by Python (ADR-0006,
    ADR-0014, ADR-0015). There is no transport to simulate, and inventing one would test a
    fiction. M9-D.1's live smoke test covers it, once, for real.
  * **the analysis itself.** That is `bops-company-analysis`, tested by
    `unit.test_m9c3_company_analysis` and unchanged by this milestone. A command test that
    re-asserted the skill's behaviour would be the duplication this command exists to avoid.

What *is* exercised against the real engine is the policy the command promises to preserve:
tier recomputation, candidate-claim status and the fail-closed paths. Those run through the
same `open_retrieval`/`close_retrieval` calls the skill uses, with fixtures standing in for
the scout reply. No network access anywhere in this file.
"""

import os
import re
import unittest

from bops import commands
from bops import research as R
from bops.commands import registry
from bops.research import scout as scout_mod

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_ID = "company-analysis"
COMMAND_MD = os.path.join(REPO, "commands", "%s.md" % COMMAND_ID)
SKILL = "bops-company-analysis"
SKILL_MD = os.path.join(REPO, "skills", SKILL, "SKILL.md")

#: The four focus values the skill's input contract defines. The command may not invent a
#: fifth, and may not quietly drop one.
SUPPORTED_FOCUS = ("overview", "developments", "positioning", "full")

COMPANY = "Northwind Logistics"
REQUEST = dict(subject=COMPANY, category=R.COMPANY, intent=R.PROFILE,
               public_terms={"industry": "logistics", "period": "2026"},
               operation="m9d1-company-command-test")

FILING = {"source": "US Securities and Exchange Commission",
          "reference": "https://www.sec.gov/Archives/northwind-10k-2026",
          "title": "Northwind Logistics Inc. Form 10-K, FY2025",
          "publication_date": "2026-03-02", "source_type": "filing",
          "content": "Revenue for fiscal 2025 was $412.6 million, up 8.1% year on year.",
          "claim_kind": "financials"}

BLOG = {"source": "Freight Insider", "reference": "https://freightinsider.example/northwind",
        "title": "What Northwind is really up to", "publication_date": "2026-06-01",
        "source_type": "blog", "content": "Northwind is said to be targeting 20% growth.",
        "claim_kind": "financials"}


def read(path):
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
    import json
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


# -- A. Registration --------------------------------------------------------------------

class TestRegistration(unittest.TestCase):

    def test_the_command_exists(self):
        self.assertTrue(os.path.exists(COMMAND_MD), COMMAND_MD)

    def test_the_command_name_is_exactly_company_analysis(self):
        self.assertEqual(os.path.basename(COMMAND_MD), "company-analysis.md")
        self.assertIn("# /company-analysis", body())

    def test_it_is_discoverable_as_a_plugin_command(self):
        """Commands auto-discover from `commands/*.md` (architecture.md section 2).

        Discovery is the file being present with a parseable frontmatter block carrying a
        description - a command that loads with no description does not route at all.
        """
        found = [n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")]
        self.assertIn(COMMAND_ID, found)
        block = frontmatter(read(COMMAND_MD))
        self.assertTrue(re.search(r"^description:\s*\S", block, re.M))

    def test_no_duplicate_registration(self):
        found = [n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                 if n.endswith(".md")]
        self.assertEqual(found.count(COMMAND_ID), 1)

    def test_it_carries_no_analytics_registry_spec(self):
        """It reads no dataset, so `commands.run()` must have nothing to run."""
        self.assertIsNone(registry.spec_for(COMMAND_ID))
        self.assertNotIn(COMMAND_ID, registry.COMMAND_IDS)
        self.assertNotIn("/%s" % COMMAND_ID, commands.catalogue_as_dict())

    def test_frontmatter_declares_only_supported_fields(self):
        supported = {"description", "argument-hint", "allowed-tools",
                     "disable-model-invocation", "hide-from-slash-command-tool"}
        declared = set(re.findall(r"^([a-zA-Z-]+):", frontmatter(read(COMMAND_MD)), re.M))
        self.assertTrue(declared <= supported, declared - supported)

    def test_frontmatter_is_single_line_per_field(self):
        """A wrapped description silently becomes a different YAML shape."""
        for line in frontmatter(read(COMMAND_MD)).split("\n"):
            self.assertFalse(line[:1] in (" ", "\t"), line[:40])


# -- B. Input ---------------------------------------------------------------------------

class TestInputContract(unittest.TestCase):

    def test_company_is_declared_required(self):
        row = [l for l in raw_lines() if l.startswith("| company ")]
        self.assertTrue(row, "no company input row")
        self.assertIn("**yes**", row[0])

    def test_missing_company_asks_and_does_not_retrieve(self):
        text = body().lower()
        self.assertIn("no company given", text)
        self.assertIn("do not choose a company", text)
        self.assertIn("do not retrieve", text)

    def test_every_supported_focus_value_is_named(self):
        text = body()
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, text, value)

    def test_an_unsupported_focus_is_rejected_rather_than_defaulted(self):
        text = body().lower()
        self.assertIn("unsupported `--focus`", text)
        self.assertIn("do not fall back to the default", text)

    def test_the_focus_values_match_the_skill_exactly(self):
        """The command may not invent a focus mode the skill cannot honour."""
        skill = read(SKILL_MD)
        row = [l for l in skill.split("\n") if l.startswith("| `focus`")]
        self.assertTrue(row, "skill declares no focus row")
        for value in SUPPORTED_FOCUS:
            self.assertIn(value, row[0], value)

    def test_optional_public_terms_are_passed_through(self):
        text = body()
        for flag in ("--industry", "--market", "--period", "--window"):
            self.assertIn(flag, text, flag)

    def test_the_window_is_not_reinterpreted_by_the_command(self):
        text = body().lower()
        self.assertIn("passed through unread", text)
        self.assertIn("do not reinterpret a date here", text)

    def test_business_context_precedence_is_not_bypassed(self):
        text = body().lower()
        self.assertIn("resolve business context", text)
        self.assertIn("do not guess it", text)

    def test_business_context_may_contribute_public_terms_only(self):
        """Context holds classified fields; only `public` ones may sharpen a query."""
        text = body().lower()
        self.assertIn("**public** disambiguating terms", body())
        self.assertIn("nothing classified above `public` may", text)

    def test_ambiguity_routes_through_the_existing_protocol(self):
        text = body().lower()
        self.assertIn("ask which", text)
        self.assertIn("do not research a guess", text)
        self.assertIn("reference/ambiguity-protocol.md", text)

    def test_it_does_not_invent_a_second_ambiguity_resolver(self):
        text = body().lower()
        self.assertIn("do not resolve ambiguity here", text)


# -- C. Thin orchestration --------------------------------------------------------------

class TestThinOrchestration(unittest.TestCase):

    def test_it_invokes_the_company_analysis_skill(self):
        self.assertIn(SKILL, body())

    def test_it_names_that_skill_as_the_single_source_of_analysis(self):
        text = body().lower()
        self.assertIn("single source of analytical behaviour", text)

    def test_it_names_no_other_skill_as_its_implementation(self):
        """Strategy is named only to refuse it; no second analytical skill is invoked."""
        named = set(re.findall(r"bops-[a-z-]+", body()))
        self.assertEqual(named - {SKILL, "bops-strategy-recommendations",
                                  "bops-research-scout"}, set())

    def test_it_declares_that_it_performs_no_research_step_itself(self):
        text = body().lower()
        self.assertIn("the command performs none of those steps itself", text)
        for verb in ("does not search", "tier a source", "build evidence",
                     "propose a claim", "verify one"):
            self.assertIn(verb, text, verb)

    def test_it_contains_no_second_research_pipeline(self):
        """No gate call, no dispatch, no ingestion written into the command."""
        text = body()
        for token in ("open_retrieval(", "close_retrieval(", "python -c",
                      "WebSearch", "WebFetch", "Task("):
            self.assertNotIn(token, text, token)

    def test_it_dispatches_no_agent_of_its_own(self):
        """The scout is named as the skill's step, never launched from this file."""
        self.assertNotIn("launch", body().lower())
        self.assertNotIn("dispatch **one**", body().lower())

    def test_it_restates_no_tiering_or_evidence_rule(self):
        """Source policy lives in reference/ and the engine; a copy here is a placement bug."""
        text = body()
        for token in ("TIER_A_PATTERNS", "FIRST_PARTY_COMPANY_DOMAINS", "tier A or B source",
                      "staleness window", "SOLE_SUPPORT_TIERS"):
            self.assertNotIn(token, text, token)

    def test_it_restates_no_kpi_formula(self):
        text = body()
        for token in ("sum(revenue) - sum(cost", "/ sum(revenue) * 100"):
            self.assertNotIn(token, text, token)

    def test_it_creates_no_verified_claim(self):
        text = body()
        self.assertIn("verified: false", text)
        self.assertNotIn("verified: true", text)
        self.assertNotIn("verified=true", text)


# -- D. Result propagation --------------------------------------------------------------

class TestResultPropagation(unittest.TestCase):

    #: The skill's fixed section order. The command reproduces, never redefines.
    SECTIONS = ("executive summary", "overview", "recent developments", "positioning",
                "business indicators", "risks and opportunities", "evidence summary",
                "conflicts", "limitations", "confidence")

    def test_all_ten_sections_are_preserved(self):
        text = body().lower()
        for section in self.SECTIONS:
            self.assertIn(section, text, section)

    def section_list(self):
        """The one enumeration of all ten sections, isolated from the rest of the text.

        Searching the whole document would match `overview` in the argument hint and
        `confidence` in the prose, so the order assertion has to run against the list
        itself rather than against first-occurrence positions.
        """
        text = body().lower()
        start = text.index("its ten sections, in its order, unchanged")
        return text[start:text.index(".", text.index("confidence", start))]

    def test_the_sections_appear_in_the_skills_order(self):
        listed = self.section_list()
        positions = [listed.index(s) for s in self.SECTIONS]
        self.assertEqual(positions, sorted(positions),
                         "command lists the sections out of the skill's order")

    def test_the_order_matches_the_skills_own_numbered_table(self):
        """Read from the skill, so a reordering there fails here rather than drifting."""
        skill = read(SKILL_MD).lower()
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", skill, re.M)
        ordered = [name for number, name in sorted(rows, key=lambda r: int(r[0]))
                   if int(number) <= 10]
        self.assertEqual(len(ordered), 10, ordered)
        listed = self.section_list()
        positions = [listed.index(name.split(" and ")[0].split("/")[0].strip()
                                  .replace("company ", ""))
                     for name in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_it_reproduces_rather_than_redefines_the_sections(self):
        text = body().lower()
        self.assertIn("its ten sections, in its order, unchanged", text)

    def test_limitations_and_confidence_are_not_footnotes(self):
        self.assertIn("never as a footnote", body().lower())

    def test_candidate_status_is_preserved(self):
        text = body().lower()
        self.assertIn("stays `candidate`", text)

    def test_unsupported_state_is_preserved(self):
        self.assertIn("stays unsupported", body().lower())

    def test_no_presentation_language_may_upgrade_a_result(self):
        text = body().lower()
        self.assertIn("nothing here may upgrade a result", text)
        self.assertIn("presentation changes wording, never status", text)

    def test_a_tier_c_source_is_not_promoted_by_the_command(self):
        self.assertIn("stays tier C", body())

    def test_it_adds_no_recommendations(self):
        text = body().lower()
        self.assertIn("no recommendations", text)
        self.assertIn("bops-strategy-recommendations", text)
        self.assertNotIn("[recommendation]", text)


# -- E. Fail-closed ---------------------------------------------------------------------

class TestFailClosed(unittest.TestCase):

    def test_every_required_failure_condition_is_covered(self):
        text = body().lower()
        for condition in ("no company given", "malformed arguments", "unsupported `--focus`",
                          "company ambiguous", "not_authorised", "retrieval failed",
                          "no reliable source found", "only tier c", "sources conflict",
                          "scout reply malformed"):
            self.assertIn(condition, text, condition)

    def test_it_declares_fail_closed_explicitly(self):
        text = body().lower()
        self.assertIn("fail closed", text)
        self.assertIn("less output, never invented output", text)

    def test_a_failed_retrieval_is_never_filled_in(self):
        text = body().lower()
        self.assertIn("never filled in from the company name", text)
        self.assertIn("training knowledge", text)

    def test_a_malformed_scout_reply_is_not_repaired_or_retried(self):
        text = body().lower()
        self.assertIn("do not repair, extract or re-dispatch", text)

    def test_a_gate_refusal_is_not_rephrased(self):
        text = body().lower()
        self.assertIn("never rephrase to get a different answer", text)

    def test_ambiguity_triggers_no_retrieval(self):
        row = [l for l in raw_lines() if l.lower().startswith("| company ambiguous")]
        self.assertTrue(row)
        self.assertIn("No retrieval", row[0])


# -- F. Policy preserved on the real engine ---------------------------------------------

class TestPolicyStillHolds(unittest.TestCase):
    """The command changed no policy. These run the real ingestion path to prove it."""

    def test_source_tier_is_recomputed_locally(self):
        result = ingest([FILING])
        item = result["evidence"]["items"][0]
        self.assertEqual(item["source_tier"], "A")

    def test_a_scout_supplied_tier_is_not_honoured(self):
        forged = dict(BLOG, source_tier="A")
        result = ingest([forged])
        self.assertEqual(result["evidence"]["items"][0]["source_tier"], "C")

    def test_a_forged_verified_field_is_not_honoured(self):
        forged = dict(BLOG, verified=True, trusted=True)
        result = ingest([forged])
        item = result["evidence"]["items"][0]
        self.assertFalse(item.get("verified", False))
        self.assertEqual(item["source_tier"], "C")

    def test_a_material_claim_on_tier_c_alone_is_still_refused(self):
        result = ingest([BLOG], proposals=[{
            "evidence_id": None, "statement": "Northwind targets 20% growth",
            "material": True}])
        self.assertEqual(result.get("candidate_claims", []), [])

    def test_a_candidate_claim_is_never_verified(self):
        result = ingest([FILING])
        evidence_id = result["evidence"]["items"][0]["evidence_id"]
        produced = ingest([FILING], proposals=[{
            "evidence_id": evidence_id,
            "statement": "Revenue for fiscal 2025 was $412.6 million", "material": True}])
        for claim in produced.get("candidate_claims", []):
            self.assertFalse(claim.get("verified", False))
            self.assertEqual(claim.get("status"), "candidate")

    def test_a_zero_record_reply_is_a_failed_retrieval_not_an_empty_analysis(self):
        result = ingest([])
        self.assertNotEqual(result.get("status"), "ok")

    def test_a_reply_from_another_operation_yields_nothing(self):
        payload = reply([FILING], "some-other-operation")
        request = dict(REQUEST)
        result = R.close_retrieval(payload, request.pop("subject"),
                                   request.pop("category"), **request)
        self.assertNotEqual(result.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
