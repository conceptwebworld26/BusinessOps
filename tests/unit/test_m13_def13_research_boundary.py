"""M13-DEF-13: internal business values never reach the external research boundary (ADR-0050).

In all three runs of the M13.2 eval case `d05`, the customer name "Fenwick Provisions" -
a value of the `Customer` column of the staged `northwind_sales.csv` - passed the disclosure
gate as a research *subject* and was briefed to `bops-research-scout`. The gate judged a
request by its shape, and a subject is public by shape.

These tests hold the provenance-aware boundary that closes it. Each builds a real workspace
in a temporary directory and runs the production gate from inside it, because the register
is deliberately not something a caller can hand to the gate: it is read from the working
directory's business data, every assessment.

"Fenwick Provisions" appears only as the regression fixture. `ProductionHasNoNamedValue`
asserts that no production file names it, and a second synthetic customer is blocked the
same way.
"""

import csv
import io
import json
import os
import shutil
import tempfile
import unittest

from bops import research as R
from bops.privacy import aggregation as agg
from bops.research import boundary as boundary_mod
from bops.research import contract as contract_mod
from bops.research import gate as gate_mod
from bops.research import retrieval as retrieval_mod
from bops.research import scout as scout_mod

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
DEMO_CSV = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
D05_CASE = os.path.join(REPO, "evals", "disclosure", "d05-tier3-customer-refused",
                        "case.yaml")

#: The d05 customer, as the regression fixture. Production code never names it.
D05_CUSTOMER = "Fenwick Provisions"

#: The three dispatched queries recorded in the M13.2 evaluations (defects.md, M13-DEF-13).
D05_OBSERVED_QUERIES = (
    "2026 Fenwick Provisions trends",
    "Fenwick Provisions company profile",
    "Fenwick Provisions 2026 company profile",
)

#: A second synthetic workspace: an account register with identifiers and amounts.
ACCOUNTS_HEADER = ["AccountNumber", "CustomerID", "AccountName", "Tag", "Region",
                   "InvoiceTotal"]
ACCOUNTS_ROWS = [
    ["ACC-778812", "100234", "Harrowgate Joinery", "Tier Gold", "North", "4312.19"],
    ["ACC-778813", "100235", "Pellmore Textiles", "Tier Silver", "South", "2210.40"],
]


def _dump(result):
    """Everything a caller would read from a result, as one searchable string."""
    return json.dumps(result, default=str)


def _dispatchable(result):
    """What could reach the scout: the brief, and nothing else crosses (ADR-0017)."""
    return _dump(result.get("brief"))


class Workspace(unittest.TestCase):
    """Run each test from inside a fresh business workspace, and restore the cwd after."""

    files = ("demo",)

    def setUp(self):
        self._cwd = os.getcwd()
        self.root = tempfile.mkdtemp(prefix="bops-def13-")
        if "demo" in self.files:
            target = os.path.join(self.root, "assets", "demo-data")
            os.makedirs(target)
            shutil.copy(DEMO_CSV, os.path.join(target, "northwind_sales.csv"))
        if "accounts" in self.files:
            with io.open(os.path.join(self.root, "accounts.csv"), "w", newline="",
                         encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(ACCOUNTS_HEADER)
                writer.writerows(ACCOUNTS_ROWS)
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.root, ignore_errors=True)

    def open(self, subject, category=R.COMPANY, **kwargs):
        kwargs.setdefault("intent", R.PROFILE)
        return R.open_retrieval(subject, category, **kwargs)

    def assertBlocked(self, result, secret=None):
        self.assertEqual(result["status"], R.NOT_AUTHORISED, result)
        self.assertIsNone(result["brief"])
        self.assertIs(result["research_performed"], False)
        self.assertIn("internal_business_value", result["failed_checks"])
        if secret is not None:
            lowered = secret.lower()
            for key in ("explanation", "reasons", "alternative"):
                self.assertNotIn(lowered, _dump(result.get(key)).lower(), key)


class PublicResearchStillWorks(Workspace):
    """Tests 1 and 12: an explicit public subject goes through the existing policy."""

    def test_a_public_company_is_authorised_at_tier_zero(self):
        opened = self.open("Microsoft", public_terms={"industry": "technology",
                                                      "period": "2026"})
        self.assertEqual(opened["status"], R.AUTHORISED)
        self.assertEqual(opened["tier"], 0)
        self.assertEqual(opened["brief"]["query_text"],
                         "Microsoft technology 2026 company profile")

    def test_public_column_values_are_not_registered(self):
        """Region and category are `public`: ordinary Tier 0 vocabulary is untouched."""
        opened = self.open("cold chain storage", R.MARKET, intent=R.TRENDS,
                           public_terms={"geographic_market": "South", "period": "2026"})
        self.assertEqual(opened["status"], R.AUTHORISED)

    def test_every_category_still_authorises_public_terms(self):
        for category, intents in contract_mod.CATEGORY_INTENTS.items():
            for intent in intents:
                opened = self.open("logistics", category, intent=intent,
                                   public_terms={"period": "2026"})
                self.assertEqual(opened["status"], R.AUTHORISED, (category, intent))

    def test_the_plugin_root_itself_is_never_read(self):
        """Its files are the synthetic demo data and fixtures, never user business data."""
        os.chdir(REPO)
        self.assertEqual(len(boundary_mod.workspace_register()), 0)


class InternalValuesAreBlocked(Workspace):
    """Tests 2 to 7."""

    files = ("demo", "accounts")

    def test_an_internal_customer_name_is_blocked_with_no_approval_path(self):
        for tier in (0, 1, 2):
            opened = self.open(D05_CUSTOMER, public_terms={"period": "2026"},
                               requested_tier=tier)
            self.assertBlocked(opened, D05_CUSTOMER)
            self.assertEqual(opened["decision"], gate_mod.REFUSE)
            self.assertIn("no approval can release", opened["explanation"])

    def test_another_customer_is_blocked_the_same_way(self):
        """The protection is the provenance, not a list of names."""
        self.assertBlocked(self.open("Harrowgate Joinery"), "Harrowgate Joinery")
        self.assertBlocked(self.open("Marchmont Retail"), "Marchmont Retail")

    def test_a_product_and_customer_combination_is_blocked(self):
        self.assertBlocked(self.open("%s Ambient Pallets" % D05_CUSTOMER), D05_CUSTOMER)

    def test_an_internal_account_identifier_is_blocked(self):
        self.assertBlocked(self.open("ACC-778812"), "ACC-778812")
        self.assertBlocked(self.open("account 100234 news"), "100234")
        self.assertBlocked(self.open("order SO-41011"), "SO-41011")

    def test_an_internal_only_label_is_blocked(self):
        """`Tag` matches no rule, so it is `internal` by default - never public."""
        self.assertBlocked(self.open("Tier Gold customers"), "Tier Gold")

    def test_an_internal_metric_is_blocked(self):
        """A row value, a computed figure and a rate: none has public provenance."""
        row_value = self.open("logistics", R.INDUSTRY, intent=R.TRENDS,
                              public_terms={"period": "2026", "our_revenue": "831.66"})
        self.assertBlocked(row_value, "831.66")
        computed = self.open("logistics", R.INDUSTRY, intent=R.TRENDS,
                             public_terms={"notes_for_search": "revenue 12,345.67"})
        self.assertBlocked(computed, "12,345.67")
        rate = self.open("logistics margin 34.5% benchmark", R.INDUSTRY, intent=R.TRENDS)
        self.assertBlocked(rate, "34.5")
        integer_amount = self.open("logistics", R.INDUSTRY, intent=R.TRENDS,
                                   public_terms={"figure": "4312.19 USD"})
        self.assertBlocked(integer_amount, "4312")

    def test_a_value_embedded_in_a_longer_query_is_blocked(self):
        subject = "latest 2026 news, filings and trends for fenwick   PROVISIONS in the uk"
        self.assertBlocked(self.open(subject), "fenwick")

    def test_a_value_in_metadata_or_context_is_blocked(self):
        cases = {
            "operation": dict(operation="company-analysis-%s-2026-09-26" % D05_CUSTOMER),
            "purpose": dict(purpose="relevant to our customer %s" % D05_CUSTOMER),
            "notes": dict(notes=["customer: %s" % D05_CUSTOMER]),
            "source requirements": dict(source_requirements={"about": D05_CUSTOMER}),
            "destination": dict(destination=contract_mod.Destination(
                "public-web-search", description="for %s" % D05_CUSTOMER)),
            "term": dict(public_terms={"competitor_1": D05_CUSTOMER}),
            "term name": dict(public_terms={D05_CUSTOMER: "x"}),
        }
        for label, kwargs in cases.items():
            opened = self.open("Microsoft", **kwargs)
            self.assertBlocked(opened, D05_CUSTOMER)
            self.assertNotIn(D05_CUSTOMER.lower(), _dispatchable(opened).lower(), label)

    def test_an_internal_value_in_metadata_has_no_approval_path_at_tier_two(self):
        """Approval covers the text shown; an operation id is not shown."""
        opened = self.open("Microsoft", requested_tier=2,
                           operation="op-Ambient Pallets-2026")
        self.assertBlocked(opened)
        self.assertEqual(opened["decision"], gate_mod.REFUSE)


class ProvenanceCannotBeRelabelled(Workspace):
    """Test 8, and the tampering routes listed in the remediation brief."""

    def test_a_descriptor_declared_public_is_still_screened(self):
        descriptor = agg.AggregateDescriptor(
            "%s order count" % D05_CUSTOMER, "10-50", agg.BANDED, 40, ("Customer",),
            "public")
        opened = self.open("logistics", R.INDUSTRY, intent=R.TRENDS,
                           derived_context=[descriptor], requested_tier=1)
        self.assertBlocked(opened, D05_CUSTOMER)

    def test_a_caller_public_flag_is_just_another_term(self):
        opened = self.open(D05_CUSTOMER, public_terms={"is_public": "true",
                                                       "safe": "yes"})
        self.assertBlocked(opened, D05_CUSTOMER)

    def test_the_register_takes_no_argument_and_cannot_be_edited(self):
        with self.assertRaises(TypeError):
            boundary_mod.workspace_register(self.root)       # noqa - deliberate misuse
        register = boundary_mod.workspace_register()
        self.assertGreater(len(register), 0)
        with self.assertRaises(AttributeError):
            register._phrases = {}
        provenance = register.matches(D05_CUSTOMER)[0]
        with self.assertRaises(AttributeError):
            provenance.sensitivity = "public"

    def test_relabelling_after_assessment_changes_nothing(self):
        descriptor = agg.AggregateDescriptor(
            "%s share" % D05_CUSTOMER, "10-20%", agg.RATE, 40, ("Customer",), "never")
        request = contract_mod.ResearchRequest(
            "logistics", R.INDUSTRY, intent=R.TRENDS, derived_context=[descriptor],
            requested_tier=1)
        decision = gate_mod.assess(request)
        self.assertTrue(decision.refused)
        descriptor.source_sensitivity = "public"
        with self.assertRaises(contract_mod.ResearchError):
            decision.decision = gate_mod.ALLOW
        with self.assertRaises(retrieval_mod.RetrievalError):
            retrieval_mod.RetrievalRequest(decision)
        self.assertTrue(gate_mod.assess(request).refused)

    def test_other_intents_and_categories_are_blocked_too(self):
        for category, intents in contract_mod.CATEGORY_INTENTS.items():
            for intent in intents:
                opened = self.open(D05_CUSTOMER, category, intent=intent)
                self.assertBlocked(opened, D05_CUSTOMER)


class ABlockedRequestNeverReachesTheScout(Workspace):
    """Tests 9 and 10."""

    def test_no_brief_exists_so_no_transport_is_called(self):
        request = contract_mod.ResearchRequest(D05_CUSTOMER, R.COMPANY, intent=R.PROFILE)
        decision = gate_mod.assess(request)
        transport = scout_mod.RecordingTransport(records=[])
        with self.assertRaises(retrieval_mod.RetrievalError):
            scout_mod.ScoutRetriever(transport=transport).retrieve(
                retrieval_mod.RetrievalRequest(decision))
        self.assertEqual(transport.calls, [])

    def test_closing_a_blocked_retrieval_assembles_no_evidence(self):
        reply = "BOPS-END/1 op-x 0"
        closed = R.close_retrieval(reply, D05_CUSTOMER, R.COMPANY, intent=R.PROFILE,
                                   operation="op-x")
        self.assertEqual(closed["status"], R.NOT_AUTHORISED)
        self.assertNotIn("evidence", closed)
        self.assertIs(closed["research_performed"], False)

    def test_no_route_around_the_gate_builds_a_brief(self):
        """The scout is briefed only from a gate-issued authorisation (ADR-0014)."""
        request = contract_mod.ResearchRequest(D05_CUSTOMER, R.COMPANY, intent=R.PROFILE)
        for impostor in (request, {"query_text": D05_CUSTOMER}, R.build(request)):
            with self.assertRaises(scout_mod.ScoutError):
                scout_mod.ScoutBrief(impostor)
        closed = R.close_retrieval_object("BOPS-END/1 op-y 0", D05_CUSTOMER, R.COMPANY,
                                          intent=R.PROFILE, operation="op-y")
        self.assertEqual(closed["status"], R.NOT_AUTHORISED)
        self.assertNotIn("evidence_set", closed)

    def test_the_refusal_is_a_privacy_block_not_an_empty_search(self):
        opened = self.open(D05_CUSTOMER)
        self.assertIn("Internal business data cannot be sent to external research",
                      opened["explanation"])
        self.assertIn("No research was performed", opened["explanation"])
        self.assertIn("not a finding that no public source exists", opened["explanation"])
        self.assertNotIn("No reliable source found", opened["explanation"])
        self.assertNotIn("evidence", opened)
        self.assertIn("'Customer' column", opened["explanation"])


class ASafeAlternativeRemains(Workspace):
    """Test 11."""

    def test_the_alternative_is_public_and_itself_authorised(self):
        opened = self.open(D05_CUSTOMER, public_terms={"industry": "food distribution",
                                                       "period": "2026"})
        alternative = opened["alternative"]
        self.assertEqual(alternative["text"], "food distribution 2026 company profile")
        self.assertNotIn("fenwick", alternative["text"].lower())
        retry = self.open("food distribution", R.INDUSTRY, intent=R.TRENDS,
                          public_terms={"period": "2026"})
        self.assertEqual(retry["status"], R.AUTHORISED)

    def test_with_no_public_term_left_the_user_is_asked_for_one(self):
        opened = self.open(D05_OBSERVED_QUERIES[0])
        self.assertIsNone(opened["alternative"]["text"])
        self.assertIn("name the industry, market or public company",
                      opened["alternative"]["explanation"])

    def test_an_aggregated_rate_still_passes_tier_one(self):
        opened = self.open("logistics", R.INDUSTRY, intent=R.TRENDS,
                           derived_context=[agg.rate_descriptor("churn", 8, 100,
                                                                entity_count=40)],
                           requested_tier=1)
        self.assertEqual(opened["status"], R.AUTHORISED)
        self.assertEqual(opened["tier"], 1)

    def test_an_internal_non_tier_three_value_is_offered_tier_two_approval(self):
        """A product name is `internal`: the existing Tier 2 path, verbatim text first."""
        request = contract_mod.ResearchRequest(
            "Ambient Pallets", R.MARKET, intent=R.TRENDS, requested_tier=2)
        decision = gate_mod.assess(request)
        self.assertEqual(decision.decision, gate_mod.ALLOW_WITH_APPROVAL)
        self.assertFalse(decision.authorised)
        self.assertEqual(decision.consent_request()["transmitted_text"],
                         decision.query_text)
        at_tier_zero = self.open("Ambient Pallets", R.MARKET, intent=R.TRENDS)
        self.assertBlocked(at_tier_zero)


class TheBoundaryFailsClosed(Workspace):
    """An unscreenable workspace refuses rather than assuming nothing is internal."""

    def test_an_unreadable_data_file_refuses(self):
        with io.open(os.path.join(self.root, "broken.xlsx"), "wb") as handle:
            handle.write(b"not a workbook")
        opened = self.open("Microsoft")
        self.assertEqual(opened["status"], R.NOT_AUTHORISED)
        self.assertIsNone(opened["brief"])
        self.assertIn(contract_mod.REASON_BOUNDARY_UNVERIFIABLE, opened["failed_checks"])
        self.assertIn("broken.xlsx", opened["explanation"])

    def test_too_many_data_files_refuses(self):
        saved = boundary_mod.MAX_FILES
        boundary_mod.MAX_FILES = 0
        try:
            opened = self.open("Microsoft")
        finally:
            boundary_mod.MAX_FILES = saved
        self.assertIn(contract_mod.REASON_BOUNDARY_UNVERIFIABLE, opened["failed_checks"])
        self.assertIsNone(opened["brief"])


class D05Regression(Workspace):
    """The d05 failure pattern, reproduced in the d05 workspace, now blocked."""

    def test_the_d05_case_stages_this_workspace(self):
        """So the reproduction below is the case's own precondition, not a lookalike."""
        with io.open(D05_CASE, encoding="utf-8") as handle:
            case = handle.read()
        self.assertIn("assets/demo-data/northwind_sales.csv", case)
        self.assertIn(D05_CUSTOMER, case)
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, "assets", "demo-data", "northwind_sales.csv")))

    def test_no_observed_d05_query_reaches_a_dispatch_payload(self):
        for query in D05_OBSERVED_QUERIES:
            for intent in (R.PROFILE, R.TRENDS):
                opened = self.open(query, intent=intent,
                                   operation="company-analysis-%s-2026-09-25" % query)
                self.assertBlocked(opened, D05_CUSTOMER)
                self.assertNotIn("fenwick", _dispatchable(opened).lower())

    def test_before_the_fix_the_same_request_would_have_been_authorised(self):
        """The gate without the register is the pre-fix gate, and it allowed d05."""
        request = contract_mod.ResearchRequest(D05_CUSTOMER, R.COMPANY, intent=R.PROFILE)
        self.assertEqual(request.validate(), [])
        self.assertEqual(boundary_mod.screen(request, boundary_mod.InternalValueRegister()),
                         [])
        self.assertTrue(boundary_mod.screen(request, boundary_mod.workspace_register()))


class ProductionHasNoNamedValue(unittest.TestCase):
    def test_no_production_file_names_the_fixture_customer(self):
        for name in ("boundary.py", "gate.py", "contract.py", "handoff.py"):
            path = os.path.join(REPO, "lib", "python", "bops", "research", name)
            with io.open(path, encoding="utf-8") as handle:
                self.assertNotIn("fenwick", handle.read().lower(), name)


if __name__ == "__main__":
    unittest.main()
