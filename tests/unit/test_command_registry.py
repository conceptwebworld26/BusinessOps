"""The command registry and the `/ask-business-data` router.

Both are pure: the registry is a declaration, and routing decides *where a question goes*
before any data is read. Testing them without a dataset is the point — a router that needs
the answer in order to decide where to look is not a router.
"""

import json
import os
import re
import unittest

from bops import commands
from bops.commands import query, registry
from bops.kpi import registry as kpi_registry

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

#: The seven internal analytics commands approved at Milestone 7.
M7_COMMANDS = (
    "business-health", "sales-analysis", "customer-analysis", "product-analysis",
    "profitability-analysis", "cash-flow-analysis", "ask-business-data",
)

#: The two commands Milestone 8 adds. Listed separately so a regression that drops an M7
#: command is still distinguishable from one that drops an M8 command.
M8_COMMANDS = ("revenue-forecast", "anomaly-detection")

EXPECTED_COMMANDS = M7_COMMANDS + M8_COMMANDS

#: Markdown surfaces that are deliberately **not** analytics commands and so carry no
#: registry spec: they run no pipeline, so `commands.run()` has nothing to run. M9-B's
#: `/retrieval-slice` is the integration harness for external retrieval - it sequences the
#: disclosure gate, a scout dispatch and result normalisation, none of which is a dataset
#: pipeline. Listing it here rather than in EXPECTED_COMMANDS keeps "every analytics
#: command is declared" a real assertion instead of a widened one.
HARNESS_COMMANDS = ("retrieval-slice",)
#: BusinessOps M3 moved the harness out of the shipped `commands/` into a developer-only location,
#: so it is no longer auto-discovered, installed or shown in the `/` menu.
HARNESS_DIR = os.path.join("dev", "harness")

#: Milestone 9-D's user-facing **research** commands. Like the harness they carry no
#: registry spec, and for the same structural reason: a research command reads no dataset,
#: so there is no `required_roles`, no analytical domain, no KPI focus and no pipeline for
#: `commands.run()` to drive. Unlike the harness they are a real capability, so they are
#: listed separately - folding them into HARNESS_COMMANDS would let a shipped user-facing
#: command hide behind a constant that means "integration scaffolding".
#:
#: M9-D.1 added the first, M9-D.2 the second, M9-D.3 the third and M9-D.5 the fourth. All
#: four now ship; the tuple below is consequently empty, which is a milestone outcome and
#: not a weakened assertion - see UNBUILT_RESEARCH_COMMANDS.
RESEARCH_COMMANDS = ("company-analysis", "market-analysis", "competitor-analysis",
                     "industry-research")

#: The research commands M9-D has not built yet. A name here must genuinely not exist as a
#: command surface. M9-D.2 removed `market-analysis`, M9-D.3 removed `competitor-analysis`
#: and M9-D.5 removed `industry-research`, each because it now ships; the assertion below
#: is unchanged in strength every time and still fails on anything else appearing.
#:
#: It is now empty, and the assertion that consumes it correspondingly proves nothing about
#: absence. What still carries weight is `test_the_approved_commands_are_declared`, which
#: pins COMMAND_IDS exactly, and the Milestone-10 absence check below - so no coverage was
#: lost when the last name left this tuple.
UNBUILT_RESEARCH_COMMANDS = ()

#: M10.2-R.14's local-join command. Like the harness and the research commands it carries
#: no registry spec, and for a structural reason of its own: it drives no pipeline
#: *directly*. It names a metric and a public benchmark subject, and the skill invokes
#: whichever existing analysis command computes that metric - so there is no single
#: `required_roles`, no one analytical domain and no fixed KPI focus a spec could declare.
#: Listed separately from RESEARCH_COMMANDS because it is neither: it reads the user's file
#: *and* retrieves a benchmark, and joining those two locally is the whole capability.
JOIN_COMMANDS = ("benchmark-comparison",)

#: The Milestone-10.3 synthesis commands that ship. M10.3.1 added the first, M10.3.2 the
#: second and M10.3.3 the third. Like the join command they carry no registry spec: they drive no single pipeline,
#: read the user's file *and* consume research, and their analytical input is a synthesis set
#: rather than a dataset - so there is no `required_roles`, analytical domain or KPI focus.
SYNTHESIS_COMMANDS = ("swot-analysis", "strategy-analysis", "decision-support",
                      "executive-report")

#: The Milestone-10 synthesis commands, none of which is built. They replace the research
#: commands as this file's source of a name that must genuinely not exist: M9-D.5 shipped
#: the last research command, so a research name can no longer play that role.
#:
#: `benchmark-comparison` is deliberately **not** here: M10.2-R.14 shipped it, and it is a
#: local-join surface rather than one of the four M10.3 synthesis commands.
#:
#: M10.3.1 shipped the SWOT as `swot-analysis` (the name `project_plan.md` gives it), so the
#: placeholder `swot` left this tuple and SYNTHESIS_COMMANDS asserts the real name present.
#: `executive-report` joined it: it was always unbuilt and is now guarded here too, so the
#: three remaining M10.3 commands carry the assertion rather than two.
#:
#: M10.3.2 shipped `strategy-analysis`, which moved to SYNTHESIS_COMMANDS; the two commands
#: still unbuilt keep the assertion at full strength.
#:
#: M10.3.3 shipped `decision-support`, which moved to SYNTHESIS_COMMANDS in turn; the one
#: command still unbuilt keeps the assertion at full strength.
#:
#: The Executive Report implementation (ADR-0033) shipped `executive-report`, the last M10.3
#: synthesis command. The tuple is consequently empty - a milestone outcome, not a weakened
#: assertion, exactly as UNBUILT_RESEARCH_COMMANDS became empty - and
#: `test_the_built_synthesis_commands_exist_and_carry_no_spec` asserts all four present.
UNBUILT_SYNTHESIS_COMMANDS = ()

#: A command belonging to a milestone that has not been built. Used wherever a test needs
#: a name the registry must genuinely not know. M9-D.5 shipped `/industry-research`, so the
#: name moved on to a Milestone-10 command; M10.3.2 shipped `/strategy-analysis`, so it moved
#: again to one still unbuilt, and M10.3.3 shipped `/decision-support`, so it moved once more.
#: The Executive Report implementation shipped the last planned command, so no planned name is
#: left to play the role: this one is deliberately not a BusinessOps command, and a test below
#: asserts no command file of that name exists either.
UNBUILT_COMMAND = "not-a-businessops-command"


class TestRegistry(unittest.TestCase):

    def test_the_approved_commands_are_declared(self):
        self.assertEqual(registry.COMMAND_IDS, EXPECTED_COMMANDS)

    def test_the_milestone_seven_commands_are_all_still_present(self):
        for command_id in M7_COMMANDS:
            self.assertIsNotNone(registry.spec_for(command_id), command_id)

    def test_every_command_has_a_markdown_orchestrator(self):
        for spec in registry.COMMANDS:
            path = os.path.join(REPO, spec.path)
            self.assertTrue(os.path.exists(path), spec.path)

    def test_every_markdown_orchestrator_is_declared(self):
        found = sorted(name[:-3] for name in os.listdir(os.path.join(REPO, "commands"))
                       if name.endswith(".md"))
        self.assertEqual(found, sorted(EXPECTED_COMMANDS
                                       + RESEARCH_COMMANDS + JOIN_COMMANDS
                                       + SYNTHESIS_COMMANDS))

    def test_no_analytics_command_is_undeclared(self):
        """Only the harness, the research, join and synthesis commands may have no spec.

        Amended by M9-D.1, which shipped `/company-analysis`, by M10.2-R.14, which shipped
        `/benchmark-comparison`, and by M10.3.1, which shipped `/swot-analysis`. The
        assertion it replaces allowed exactly one exception (the harness); this one allows
        exactly four named sets and still fails on any *other* undeclared markdown surface,
        which is the property worth having - a new analytics command cannot skip
        declaration.
        """
        found = sorted(name[:-3] for name in os.listdir(os.path.join(REPO, "commands"))
                       if name.endswith(".md"))
        undeclared = set(found) - set(EXPECTED_COMMANDS)
        self.assertEqual(undeclared,
                         set(RESEARCH_COMMANDS)
                         | set(JOIN_COMMANDS) | set(SYNTHESIS_COMMANDS))

    def test_the_retrieval_harness_is_developer_only_and_not_shipped(self):
        """BusinessOps M3: the harness lives in `dev/harness/`, never in the shipped `commands/`."""
        shipped = os.listdir(os.path.join(REPO, "commands"))
        for name in HARNESS_COMMANDS:
            self.assertNotIn(name + ".md", shipped)
            self.assertTrue(os.path.isfile(os.path.join(REPO, HARNESS_DIR, name + ".md")))

    def test_the_retrieval_harness_is_not_a_runnable_analytics_command(self):
        """It has no pipeline; `commands.run` must not pretend otherwise."""
        for name in HARNESS_COMMANDS:
            self.assertIsNone(registry.spec_for(name))
            self.assertNotIn(name, registry.COMMAND_IDS)

    def test_a_research_command_is_not_a_runnable_analytics_command(self):
        """Same reason as the harness: no dataset, so nothing for `commands.run` to run.

        This is the assertion that keeps `/company-analysis` honest. Were it ever given a
        registry spec it would acquire `required_roles`, an analytics domain and a KPI
        focus - none of which a public-source research command has - and `commands.run`
        would start driving a dataset pipeline for a command that reads no dataset.
        """
        for name in RESEARCH_COMMANDS:
            self.assertIsNone(registry.spec_for(name))
            self.assertNotIn(name, registry.COMMAND_IDS)
            with self.assertRaises(KeyError):
                registry.require(name)

    def test_the_unbuilt_research_commands_still_do_not_exist(self):
        """M9-D.1, D.2, D.3 and D.5 shipped all four, so the tuple is now empty."""
        present = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                   if n.endswith(".md")}
        self.assertEqual(present & set(UNBUILT_RESEARCH_COMMANDS), set())
        for name in UNBUILT_RESEARCH_COMMANDS:
            self.assertIsNone(registry.spec_for(name))

    def test_the_four_research_commands_all_exist(self):
        """The other half of the statement above, so an empty tuple cannot pass by being
        empty: every research command the tuple stopped guarding is asserted present."""
        present = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                   if n.endswith(".md")}
        for name in RESEARCH_COMMANDS:
            self.assertIn(name, present, name)
            self.assertIsNone(registry.spec_for(name))

    def test_the_unbuilt_synthesis_commands_do_not_exist(self):
        """Milestone 10 is not built. These names must not appear as a command surface."""
        present = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                   if n.endswith(".md")}
        self.assertEqual(present & set(UNBUILT_SYNTHESIS_COMMANDS), set())
        for name in UNBUILT_SYNTHESIS_COMMANDS:
            self.assertIsNone(registry.spec_for(name))
            self.assertNotIn(name, registry.COMMAND_IDS)

    def test_the_built_synthesis_commands_exist_and_carry_no_spec(self):
        """The other half of the absence check, so a shipped name is asserted present."""
        present = {n[:-3] for n in os.listdir(os.path.join(REPO, "commands"))
                   if n.endswith(".md")}
        for name in SYNTHESIS_COMMANDS:
            self.assertIn(name, present, name)
            self.assertIsNone(registry.spec_for(name))
            self.assertNotIn(name, registry.COMMAND_IDS)
        self.assertEqual(set(SYNTHESIS_COMMANDS) & set(UNBUILT_SYNTHESIS_COMMANDS), set())

    def test_each_command_declares_its_downstream_implementation(self):
        table = registry.mapping_table()
        self.assertEqual(table["/sales-analysis"], "bops-sales-intelligence")
        self.assertEqual(table["/customer-analysis"], "bops-customer-intelligence")
        self.assertEqual(table["/product-analysis"], "bops-product-intelligence")
        self.assertEqual(table["/profitability-analysis"], "bops-financial-analysis")
        self.assertEqual(table["/cash-flow-analysis"], "bops-financial-analysis")
        self.assertEqual(table["/business-health"], "cross-domain orchestration")
        self.assertEqual(table["/ask-business-data"],
                         "routing over internal analytics")

    def test_every_named_skill_exists(self):
        for spec in registry.COMMANDS:
            if not spec.skill:
                continue
            self.assertTrue(
                os.path.exists(os.path.join(REPO, "skills", spec.skill, "SKILL.md")),
                spec.skill)

    def test_every_declared_domain_is_a_real_analytical_domain(self):
        from bops import analytics
        known = {name for name, _fn in analytics.DOMAINS}
        for spec in registry.COMMANDS:
            for domain in spec.domains:
                self.assertIn(domain, known, spec.command_id)

    def test_every_focus_metric_exists_in_the_kpi_catalogue(self):
        for spec in registry.COMMANDS:
            for kpi_id in spec.kpi_focus:
                self.assertIn(kpi_id, kpi_registry.BY_ID, kpi_id)

    def test_every_declared_section_has_a_renderer(self):
        from bops.commands import sections
        for spec in registry.COMMANDS:
            for section in spec.sections:
                self.assertIn(section, sections.RENDERERS, section)

    def test_catalogue_is_machine_readable(self):
        document = commands.catalogue_as_dict()
        self.assertEqual(document["count"], len(EXPECTED_COMMANDS))
        json.dumps(document)

    def test_an_unknown_command_is_refused_by_name(self):
        self.assertIsNone(registry.spec_for(UNBUILT_COMMAND))
        with self.assertRaises(KeyError) as caught:
            registry.require(UNBUILT_COMMAND)
        self.assertIn(UNBUILT_COMMAND, str(caught.exception))
        self.assertFalse(os.path.exists(os.path.join(REPO, "commands",
                                                     UNBUILT_COMMAND + ".md")))

    def test_a_leading_slash_is_accepted(self):
        self.assertIs(registry.spec_for("/sales-analysis"),
                      registry.spec_for("sales-analysis"))

    def test_commands_restate_no_kpi_formula(self):
        """A command is an orchestrator. A formula found in one is a placement bug."""
        for name in os.listdir(os.path.join(REPO, "commands")):
            text = open(os.path.join(REPO, "commands", name), encoding="utf-8").read()
            for token in ("sum(revenue) - sum(cost", "/ sum(revenue) * 100"):
                self.assertNotIn(token, text, name)

    def test_command_frontmatter_uses_only_supported_fields(self):
        supported = {"description", "argument-hint", "allowed-tools",
                     "disable-model-invocation", "hide-from-slash-command-tool"}
        for name in os.listdir(os.path.join(REPO, "commands")):
            text = open(os.path.join(REPO, "commands", name), encoding="utf-8").read()
            self.assertTrue(text.startswith("---"), name)
            block = text.split("---", 2)[1]
            fields = set(re.findall(r"^([a-zA-Z-]+):", block, re.M))
            self.assertTrue(fields <= supported, "%s: %s" % (name, fields - supported))


class TestQueryVocabulary(unittest.TestCase):

    def test_metric_keywords_come_from_the_catalogue(self):
        vocabulary = query.kpi_vocabulary()
        self.assertEqual(sorted(vocabulary), sorted(kpi_registry.BY_ID))
        self.assertIn("margin", vocabulary["gross_margin"][1])
        self.assertIn("ebitda", vocabulary["ebitda"][1])

    def test_bracketed_abbreviations_are_askable(self):
        vocabulary = query.kpi_vocabulary()
        self.assertIn("dso", vocabulary["days_sales_outstanding"][1])
        self.assertIn("nrr", vocabulary["net_revenue_retention"][1])

    def test_dimension_keywords_come_from_the_semantic_roles(self):
        vocabulary = query.dimension_vocabulary()
        self.assertEqual(sorted(vocabulary),
                         ["category", "customer", "product", "region", "salesperson"])
        self.assertIn("categories", vocabulary["category"])

    def test_answerable_concepts_are_enumerable_for_a_clarification_reply(self):
        concepts = query.answerable_concepts()
        self.assertIn("gross_margin", concepts["metrics"])
        self.assertIn("region", concepts["dimensions"])
        self.assertIn("concentration", concepts["intents"])


class TestRouting(unittest.TestCase):

    def route(self, question):
        return query.route(question)

    def test_a_metric_question_routes_to_that_metric(self):
        routing = self.route("What was our gross margin?")
        self.assertEqual(routing.status, query.ROUTED)
        self.assertEqual(routing.concept_kind, query.KPI)
        self.assertEqual(routing.concept_id, "gross_margin")

    def test_a_bare_metric_beats_a_longer_one_that_shares_a_word(self):
        self.assertEqual(self.route("What was revenue?").concept_id, "revenue")
        self.assertEqual(self.route("What was revenue growth?").concept_id,
                         "revenue_growth")

    def test_a_dimension_with_an_intent_routes_to_the_analytics_layer(self):
        routing = self.route("Which region grew fastest?")
        self.assertEqual(routing.status, query.ROUTED)
        self.assertEqual(routing.concept_kind, query.DIMENSION)
        self.assertEqual(routing.dimension, "region")
        self.assertEqual(routing.intent, "movement")
        self.assertEqual(routing.domain, "sales")

    def test_customer_and_product_dimensions_route_to_their_own_domains(self):
        self.assertEqual(self.route("Which customer is largest?").domain, "customer")
        self.assertEqual(self.route("Which product is largest?").domain, "product")
        self.assertEqual(self.route("Which category is largest?").domain, "product")

    def test_a_phrase_intent_is_recognised(self):
        routing = self.route("How many customers purchased more than once?")
        self.assertEqual(routing.intent, "repeat")

    def test_a_dimension_without_an_intent_asks_what_to_report(self):
        routing = self.route("Tell me about regions")
        self.assertEqual(routing.status, query.CLARIFICATION_NEEDED)
        self.assertEqual(routing.candidates, ["region"])

    def test_two_dimensions_ask_for_one_at_a_time(self):
        routing = self.route("Which region and product grew fastest?")
        self.assertEqual(routing.status, query.CLARIFICATION_NEEDED)
        self.assertEqual(routing.candidates, ["product", "region"])

    def test_an_unrecognised_question_asks_for_clarification_not_a_guess(self):
        routing = self.route("What is the weather in Leeds?")
        self.assertEqual(routing.status, query.CLARIFICATION_NEEDED)
        self.assertIsNone(routing.concept_id)

    def test_an_empty_question_asks_for_one(self):
        for value in ("", "   ", None):
            self.assertEqual(self.route(value).status, query.CLARIFICATION_NEEDED)

    def test_forecasting_is_refused_by_name(self):
        for question in ("What will revenue be next quarter?",
                         "Forecast our sales", "Predict margin for next year"):
            routing = self.route(question)
            self.assertEqual(routing.status, query.UNSUPPORTED, question)
            self.assertIn("forecasting", routing.reason)
            self.assertIn("/revenue-forecast", routing.reason)
            self.assertNotIn("Milestone", routing.reason)

    def test_anomaly_detection_is_refused_by_name(self):
        routing = self.route("Are there any anomalies or fraud in this data?")
        self.assertEqual(routing.status, query.UNSUPPORTED)
        self.assertIn("anomaly detection", routing.reason)

    def test_external_research_is_refused_by_name(self):
        routing = self.route("How do we compare to competitors?")
        self.assertEqual(routing.status, query.UNSUPPORTED)
        self.assertIn("external research", routing.reason)
        self.assertIn("/competitor-analysis", routing.reason)
        self.assertNotIn("Milestone", routing.reason)

    def test_a_sub_period_question_is_flagged_not_silently_widened(self):
        routing = self.route("What was revenue last quarter?")
        self.assertEqual(routing.status, query.ROUTED)
        self.assertEqual(routing.period_qualifier, "last quarter")

    def test_routing_is_deterministic(self):
        question = "Which region grew fastest?"
        first = json.dumps(self.route(question).as_dict(), sort_keys=True)
        for _attempt in range(3):
            self.assertEqual(json.dumps(self.route(question).as_dict(), sort_keys=True),
                             first)

    def test_routing_is_serialisable(self):
        json.dumps(self.route("What was our gross margin?").as_dict())


if __name__ == "__main__":
    unittest.main()
