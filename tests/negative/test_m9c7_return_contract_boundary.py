"""M9-C.7 — the parser is the enforcement, because the runtime provides none.

M9-C.1 made the return contract unambiguous: one bare `bops.scout.result/1` object, no
fences, no prose. Four live dispatches since then — three in M9-C.5, one in M9-C.6 — all
returned fenced JSON wrapped in prose anyway. Instruction-strengthening was tried and
measured, and it did not change model behaviour.

The M9-C.7 investigation then established that nothing in the runtime can enforce it:
subagent frontmatter has no output-schema field, the Task dispatch takes no schema, and
subagents return unstructured text by design. A `SubagentStop` hook can observe and block
but cannot rewrite, and blocking means "keep going", which is a retry.

So the trust boundary is `parse_result()`, and these tests defend the two ways it could be
lost:

  * **by pretending** — someone adds `output-schema:` to the agent frontmatter, the
    validator silently ignores it (proved during the investigation), and the project now
    believes it has an enforcement mechanism that does nothing. `TestNoInertEnforcementIsDeclared`
    makes that fail loudly.
  * **by helpfulness** — someone teaches the parser to find the JSON inside the prose,
    because that would have made four live retrievals "work". `TestObservedLiveShapesAreRejected`
    pins the real shapes as failures.

The rejection matrix itself lives in `test_m9c1_bare_envelope_contract.py` and is not
duplicated here. This file covers only what the runtime investigation newly justifies.
"""

import json
import os
import re
import unittest

from bops import research as R
from bops.research import scout as scout_mod

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCOUT_MD = os.path.join(REPO, "agents", "bops-research-scout.md")

#: Every frontmatter field the subagent runtime actually supports, from the Claude Code
#: subagent documentation checked during the M9-C.7 investigation (2026-09-11). Recorded
#: here so the next person does not have to re-derive it to know what is real.
SUPPORTED_AGENT_FRONTMATTER = frozenset({
    "name", "description", "tools", "disallowedTools", "model", "permissionMode",
    "maxTurns", "skills", "mcpServers", "hooks", "memory", "background", "effort",
    "isolation", "color", "initialPrompt", "experimental",
})

#: Fields that sound like they would constrain a subagent's output and do not exist. The
#: validator ignores unknown keys silently, so declaring one buys nothing but false comfort.
NON_EXISTENT_ENFORCEMENT_FIELDS = (
    "output-schema", "output_schema", "response-format", "response_format",
    "structured-output", "structured_output", "output-format", "output_format",
    "schema", "json-mode", "json_mode", "returns", "return-schema",
)

REQUEST = dict(subject="gross margin benchmark", category=R.INDUSTRY, intent=R.BENCHMARK,
               public_terms={"industry": "logistics", "period": "2026"},
               operation="m9c7-boundary-test")

RECORD = {"source": "Reuters", "reference": "https://www.reuters.com/business/margins",
          "title": "Where the margin went", "publication_date": "2026-02-11",
          "source_type": "press", "content": "Operators reported thinner margins.",
          "claim_kind": "financials"}


def read_scout():
    return open(SCOUT_MD, "rb").read().decode("utf-8")


def envelope_text():
    brief = R.open_retrieval(**REQUEST)["brief"]
    return json.dumps({"envelope": scout_mod.SCOUT_RESULT_ENVELOPE,
                       "operation": brief["operation"],
                       "query_text": brief["query_text"],
                       "status": scout_mod.RESULT_OK, "records": [RECORD]})


def close(payload):
    fields = dict(REQUEST)
    subject = fields.pop("subject")
    category = fields.pop("category")
    return R.close_retrieval(payload, subject, category, as_of="2026-09-11", **fields)


# ---------------------------------------------------------------------------
# A. No inert enforcement mechanism may be declared
# ---------------------------------------------------------------------------

class TestNoInertEnforcementIsDeclared(unittest.TestCase):
    """A field the runtime ignores is worse than no field: it looks like a control."""

    def frontmatter(self):
        return re.match(r"^---\n(.*?)\n---", read_scout(), re.S).group(1)

    def declared_fields(self):
        return set(re.findall(r"^([A-Za-z_-]+):", self.frontmatter(), re.M))

    def test_the_scout_declares_only_fields_the_runtime_supports(self):
        unsupported = self.declared_fields() - SUPPORTED_AGENT_FRONTMATTER
        self.assertEqual(unsupported, set(),
                         "declared frontmatter the subagent runtime does not read")

    def test_no_output_schema_style_field_is_declared(self):
        declared = self.declared_fields()
        for field in NON_EXISTENT_ENFORCEMENT_FIELDS:
            self.assertNotIn(field, declared,
                             "%r does not exist in the subagent runtime; declaring it "
                             "would be silently ignored and would misrepresent the "
                             "boundary as enforced" % field)

    def test_the_tool_grant_is_still_the_only_hard_control(self):
        """What the runtime *does* enforce is the tool list. That must stay exact."""
        tools = re.search(r"^tools:\s*(.+)$", self.frontmatter(), re.M).group(1)
        self.assertEqual([t.strip() for t in tools.split(",")], ["WebSearch", "WebFetch"])

    def test_the_contract_is_still_stated_for_the_model_to_follow(self):
        """Instructions are not enforcement, but dropping them would help nothing.

        Retargeted by M9-C.15: the contract the document states is now the adopted line
        protocol (ADR-0017). The point of the test is unchanged - the scout is told, in terms
        it cannot mistake for a style note, exactly what to return.
        """
        body = read_scout()
        self.assertIn("BOPS-REC/1", body)
        self.assertIn("BOPS-END/1", body)
        self.assertIn("One record per `BOPS-REC/1` line", body)
        self.assertIn("There is no second return format", body)


# ---------------------------------------------------------------------------
# B. The shapes live dispatches actually produced are failures
# ---------------------------------------------------------------------------

class TestObservedLiveShapesAreRejected(unittest.TestCase):
    """Four real dispatches, four wrapped replies. Each must stay a failure."""

    def assert_rejected(self, payload, label):
        result = close(payload)
        self.assertNotEqual(result["status"], R.OK, label)
        self.assertIsNone(result["evidence"], "%s produced an evidence set" % label)
        self.assertTrue(result["explanation"], "%s failed without saying why" % label)
        return result

    def test_m9b_shape_preamble_fence_trailing_notes(self):
        self.assert_rejected(
            "Retrieval complete for the entity implied by the fixed query.\n\n"
            "**Note on conflicting figures**: sources disagree sharply.\n\n"
            "```json\n%s\n```\n\n"
            "Additional notes for the requesting agent, outside the envelope:\n"
            "- Two candidate pages returned HTTP 403.\n" % envelope_text(),
            "M9-B shape")

    def test_m9c5_profile_shape_fence_then_process_notes(self):
        self.assert_rejected(
            "```json\n%s\n```\n\n"
            "Notes on process: the query_text and operation were used exactly as provided "
            "in the brief, unmodified. Two pages were fetched out of the max_fetched=8 "
            "allowance.\n" % envelope_text(),
            "M9-C.5 profile shape")

    def test_m9c5_positioning_shape_fence_then_bulleted_notes(self):
        self.assert_rejected(
            "```json\n%s\n```\n\n"
            "A few notes on this batch, outside the returned JSON (not part of the "
            "envelope):\n\n"
            "- Cloud market-share figures conflict across sources by design.\n"
            "- The 6sense record has no available publication date.\n" % envelope_text(),
            "M9-C.5 positioning shape")

    def test_m9c6_shape_fence_then_parent_agent_notes(self):
        self.assert_rejected(
            "```json\n%s\n```\n\n"
            "Notes for the parent agent (outside the returned envelope): The two retrieved "
            "sources materially disagree.\n" % envelope_text(),
            "M9-C.6 shape")

    def test_the_same_records_in_the_adopted_protocol_are_accepted(self):
        """The records inside every one of those replies were themselves valid.

        That is the whole reason the temptation to extract existed, and the whole reason it
        was refused: extracting would mean trusting a boundary the runtime does not draw.
        M9-C.15 removed the temptation instead of indulging it - the same records, written
        as operation-bound lines, are ingested, and the surrounding prose is simply content.

        Retargeted by M9-C.15: was `test_the_same_envelope_bare_is_accepted`. The envelope
        is no longer a scout contract, so "correctly formatted" now means the line protocol.
        """
        result = close(scout_mod.render_reply(REQUEST["operation"], [RECORD]))
        self.assertEqual(result["status"], R.OK)
        self.assertEqual(result["accepted"], 1)

    def test_those_shapes_stay_refused_even_now_that_prose_is_allowed(self):
        """Prose around *record lines* is content. Prose around an envelope is still nothing.

        Added by M9-C.15. The four live shapes above are refused for a new reason - they
        carry no `BOPS-END/1` line for this retrieval - and it matters that they are still
        refused rather than partially salvaged.
        """
        result = close("Here are my findings.\n\n```json\n%s\n```\n" % envelope_text())
        self.assertNotEqual(result["status"], R.OK)
        self.assertIsNone(result["evidence"])


# ---------------------------------------------------------------------------
# C. A contract violation is a research outcome, not a crash or a silence
# ---------------------------------------------------------------------------

class TestViolationIsReportedHonestly(unittest.TestCase):

    WRAPPED = None

    def setUp(self):
        self.WRAPPED = "Here are my findings.\n\n```json\n%s\n```\n" % envelope_text()

    def test_it_names_the_contract_it_was_reading_against(self):
        """Retargeted by M9-C.15: the contract named is now the line protocol."""
        result = close(self.WRAPPED)
        self.assertIn(scout_mod.END_TOKEN, result["explanation"])
        self.assertEqual(result["reason"], "retrieval_unavailable")

    def test_it_says_nothing_could_be_cited(self):
        """The operational consequence: the whole retrieval is lost, not just the prose."""
        self.assertIn("nothing", close(self.WRAPPED)["explanation"].lower())

    def test_it_is_a_structured_failure_not_an_exception(self):
        result = close(self.WRAPPED)
        self.assertIn("status", result)
        self.assertIn("reason", result)

    def test_no_records_leak_through_on_a_violation(self):
        result = close(self.WRAPPED)
        self.assertIsNone(result["evidence"])
        self.assertNotIn("items", result)

    def test_parsing_the_wrapped_reply_never_raises(self):
        brief = None
        records, failure = scout_mod.parse_result(self.WRAPPED, brief)
        self.assertEqual(records, [])
        self.assertIsNotNone(failure)

    def test_a_violation_cannot_be_turned_into_a_claim(self):
        """No path from a rejected reply to a candidate claim, however it is proposed."""
        fields = dict(REQUEST)
        subject = fields.pop("subject")
        category = fields.pop("category")
        result = R.close_retrieval(
            self.WRAPPED, subject, category, as_of="2026-09-11",
            proposals=[{"evidence_id": "ev-anything", "statement": "A source said so.",
                        "material": True}], **fields)
        self.assertNotEqual(result["status"], R.OK)
        self.assertEqual(result.get("candidate_claims", []), [])


if __name__ == "__main__":
    unittest.main()
