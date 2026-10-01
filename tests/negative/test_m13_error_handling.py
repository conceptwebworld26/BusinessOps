"""M13.1 deterministic gap closure for `architecture.md` section 16 (ADR-0039 section C).

Coverage-matrix row **S1-05** - *Unsupported KPI*: "Insufficient data to calculate this
metric reliably" + the inputs needed.

Existing suites prove that an unsupported metric is `unavailable` and names its missing
field (`integration.test_kpi_engine.TestUnavailablePath`), but no test pinned the section 16
statement itself. These tests assert the behaviour section 16 requires, on synthetic data,
and change nothing in the engine.
"""

import shutil
import tempfile
import unittest

from bops import pipeline
from bops.kpi import contract as kpi_contract

from fixtures import build_kpi_fixtures as kpi_fixtures

SECTION_16_STATEMENT = "Insufficient data to calculate this metric reliably."


class UnsupportedKpiStatement(unittest.TestCase):
    """A sales-only extract cannot support the cash, balance-sheet, SaaS or pipeline KPIs."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m13-s1-05-")
        cls.result = pipeline.run(kpi_fixtures.sales_only(cls.directory),
                                  load_context_files=False)
        cls.unsupported = {kpi_id: r for kpi_id, r in cls.result.kpis.items()
                           if r.status == kpi_contract.UNAVAILABLE and r.missing_inputs}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def test_the_extract_leaves_metrics_unsupported(self):
        self.assertFalse(self.result.halted, self.result.halt_reason)
        self.assertTrue(self.unsupported, "the sales-only fixture unsupported no metric")

    def test_every_unsupported_metric_states_the_section_16_sentence(self):
        for kpi_id, result in sorted(self.unsupported.items()):
            with self.subTest(kpi=kpi_id):
                self.assertTrue(result.reason.startswith(SECTION_16_STATEMENT), result.reason)

    def test_every_unsupported_metric_names_each_input_it_needs(self):
        for kpi_id, result in sorted(self.unsupported.items()):
            for field in result.missing_inputs:
                with self.subTest(kpi=kpi_id, field=field):
                    self.assertIn(field, result.reason)

    def test_an_unsupported_metric_carries_no_value(self):
        for kpi_id, result in sorted(self.unsupported.items()):
            with self.subTest(kpi=kpi_id):
                self.assertIsNone(result.value)

    def test_supported_metrics_still_compute_beside_the_unsupported_ones(self):
        self.assertEqual(self.result.kpis["revenue"].status, kpi_contract.AVAILABLE)
