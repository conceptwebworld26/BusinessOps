"""The `bops-research-scout` capability boundary.

This is the test ADR-0006 required and ADR-0014 relocated: it ships with the component
whose security property it proves, not with a milestone number.

The property under test is not "the agent behaves well" — it is that the agent performing
external retrieval **cannot read business data at all**. That is what makes BusinessOps's
internal/external boundary structural rather than advisory (ADR-0006, ADR-0009, ADR-0014),
and it is what `README.md` promises users: "the agent that performs web research has no
file-system access and cannot read your data even if instructed to."

A grant of `Read` to this agent would silently turn a structural guarantee back into a
written policy, and nothing else in the suite would notice. That is why the assertion is
against the declared tool grant rather than against behaviour.
"""

import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCOUT = os.path.join(REPO, "agents", "bops-research-scout.md")

#: Tools that would give the scout a path to the dataset, the repository or the shell.
#: Anything able to read a file, list a directory, run a command or spawn another agent
#: defeats the boundary, so the list is deny-by-name rather than allow-by-judgement.
FORBIDDEN_TOOLS = (
    "Read", "Write", "Edit", "NotebookEdit", "Bash", "BashOutput", "KillShell",
    "Glob", "Grep", "LS", "NotebookRead", "Task", "Agent", "SlashCommand",
)

#: The only tools retrieval actually needs.
PERMITTED_TOOLS = ("WebSearch", "WebFetch")


def frontmatter(path):
    raw = open(path, "rb").read().decode("utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    assert match, "%s has no frontmatter block" % path
    return match.group(1)


def field(block, name):
    match = re.search(r"^%s:\s*(.+)$" % re.escape(name), block, re.M)
    return match.group(1).strip() if match else None


class TestScoutExists(unittest.TestCase):

    def test_the_scout_is_defined(self):
        self.assertTrue(os.path.exists(SCOUT),
                        "bops-research-scout ships with M9; see ADR-0014")

    def test_it_declares_only_supported_frontmatter_fields(self):
        supported = {"name", "description", "tools", "model", "color"}
        fields = set(re.findall(r"^([a-zA-Z-]+):", frontmatter(SCOUT), re.M))
        self.assertTrue(fields <= supported, fields - supported)

    def test_it_is_named_by_convention(self):
        self.assertEqual(field(frontmatter(SCOUT), "name"), "bops-research-scout")


class TestScoutHasNoFileAccess(unittest.TestCase):
    """The security control itself."""

    def tools(self):
        declared = field(frontmatter(SCOUT), "tools")
        self.assertIsNotNone(declared, "the scout must declare an explicit tool grant")
        return [t.strip() for t in declared.split(",") if t.strip()]

    def test_the_tool_grant_is_explicit(self):
        """An absent `tools` field inherits everything — the opposite of a boundary."""
        self.assertTrue(self.tools())

    def test_it_is_granted_no_file_or_shell_tool(self):
        granted = self.tools()
        for forbidden in FORBIDDEN_TOOLS:
            self.assertNotIn(forbidden, granted,
                             "%s would give the retrieval agent a path to the dataset"
                             % forbidden)

    def test_it_is_granted_only_web_tools(self):
        for tool in self.tools():
            self.assertIn(tool, PERMITTED_TOOLS,
                          "%s is outside the retrieval grant" % tool)

    def test_it_cannot_spawn_another_agent(self):
        """Delegation would let it borrow capabilities it was denied."""
        granted = self.tools()
        for delegating in ("Task", "Agent"):
            self.assertNotIn(delegating, granted)

    def test_it_can_actually_retrieve(self):
        """A boundary that also prevents the job is not the boundary we want."""
        granted = self.tools()
        self.assertTrue(set(granted) & set(PERMITTED_TOOLS))


class TestScoutContract(unittest.TestCase):
    """The rules the definition must state, because the model reads them at runtime."""

    def body(self):
        return open(SCOUT, "rb").read().decode("utf-8").lower()

    def test_it_states_that_retrieved_content_is_not_instruction(self):
        body = self.body()
        self.assertIn("data, never instruction", body)

    def test_it_states_that_it_cannot_raise_the_disclosure_tier(self):
        self.assertIn("disclosure tier", self.body())

    def test_it_states_that_the_query_is_fixed(self):
        self.assertIn("the query is fixed", self.body())

    def test_it_requires_citations(self):
        body = self.body()
        self.assertIn("citation", body)
        self.assertIn("no reliable source found", body)

    def test_it_excludes_tier_d_sources(self):
        self.assertIn("tier d", self.body())

    def test_it_refuses_to_resolve_conflicts_silently(self):
        body = self.body()
        self.assertIn("do not average", body)

    def test_it_forbids_fabrication(self):
        self.assertIn("never fabricate", self.body())

    def test_the_description_names_the_no_access_property(self):
        description = field(frontmatter(SCOUT), "description") or ""
        self.assertIn("no file-system", description.lower())


class TestNoOtherAgentsYet(unittest.TestCase):
    """Only the scout moves forward from M11 (ADR-0014, decision D).

    Amended by the M11 verification implementation, which ships `bops-analysis-verifier`
    (ADR-0034, ADR-0035); its own boundary test is `test_m11_verifier_agent_boundary.py`.
    `bops-data-profiler` remains unbuilt, and no other agent may appear.
    """

    def test_the_remaining_m11_agents_are_not_built(self):
        agents_dir = os.path.join(REPO, "agents")
        if not os.path.isdir(agents_dir):
            self.skipTest("no agents directory")
        present = sorted(n[:-3] for n in os.listdir(agents_dir) if n.endswith(".md"))
        self.assertEqual(present, ["bops-analysis-verifier", "bops-research-scout"],
                         "bops-data-profiler remains in M11; no other agent exists")



class TestScoutIntegrationBoundary(unittest.TestCase):
    """M9-B: the integration layer must not hand the scout what the manifest denies it.

    The tool grant stops the scout *reaching* internal data. This class checks the other
    direction - that the integration does not simply pass internal data in, which would
    make the capability boundary irrelevant without touching the manifest.
    """

    def brief(self, **kwargs):
        from bops import research as R
        from bops.research import scout as scout_mod
        fields = {"subject": "churn", "category": R.INDUSTRY,
                  "public_terms": {"business_model": "B2B SaaS"}, "operation": "op"}
        fields.update(kwargs)
        request = R.ResearchRequest(**fields)
        return scout_mod.ScoutBrief(R.RetrievalRequest(R.assess(request)))

    def test_the_brief_has_exactly_the_permitted_fields(self):
        self.assertEqual(sorted(self.brief().as_dict()),
                         ["destination", "max_fetched", "max_results", "operation",
                          "query_text", "timeout_seconds"])

    def test_the_brief_type_declares_no_internal_slot(self):
        from bops.research import scout as scout_mod
        forbidden = ("request", "decision", "context", "business_context", "dataset",
                     "rows", "records", "descriptors", "derived_context", "public_terms",
                     "approval", "credentials", "secrets", "conversation", "kpis")
        for name in forbidden:
            self.assertNotIn(name, scout_mod.ScoutBrief.__slots__, name)

    def test_the_brief_cannot_be_built_from_anything_but_an_authorisation(self):
        from bops import research as R
        from bops.research import scout as scout_mod
        request = R.ResearchRequest("x", R.MARKET, public_terms={"industry": "y"})
        for bad in (request, R.build(request), "query", {"query_text": "x"}, None):
            with self.assertRaises(scout_mod.ScoutError):
                scout_mod.ScoutBrief(bad)

    def test_the_transport_sees_only_the_brief(self):
        from bops import research as R
        from bops.research import scout as scout_mod
        transport = scout_mod.RecordingTransport([])
        scout = scout_mod.ScoutRetriever(transport)
        request = R.ResearchRequest("churn", R.INDUSTRY,
                                    public_terms={"business_model": "B2B SaaS"})
        scout.retrieve(R.RetrievalRequest(R.assess(request)), as_of="2026-03-01")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(sorted(transport.calls[0]),
                         ["destination", "max_fetched", "max_results", "operation",
                          "query_text", "timeout_seconds"])

    def test_the_integration_declares_no_tool_of_its_own(self):
        """Only the manifest grants tools. The Python layer must name none."""
        import os
        import re
        from bops.research import scout as scout_mod
        text = open(scout_mod.__file__, encoding="utf-8").read()
        code = "\n".join(line.split("#")[0] for line in text.split("\n"))
        code = re.sub(r'""".*?"""', "", code, flags=re.S)
        for tool in ("WebSearch", "WebFetch", "Read", "Bash", "Task", "Agent"):
            self.assertNotIn(tool, code,
                             "%s named in scout integration code" % tool)

if __name__ == "__main__":
    unittest.main()
