"""Tier 2 — the managed runtime, read out of process (ADR-0008).

Tier 2 needs an interpreter that has openpyxl but is not this one. Where the managed runtime
is absent, these tests locate any sibling interpreter with openpyxl and use it as a stand-in;
if none exists they skip, rather than installing anything. **No test here ever bootstraps** —
installation requires explicit user consent and is exercised only through mocks.
"""

import os
import shutil
import sys
import tempfile
import unittest

from bops.errors import ConsentRequiredError
from bops.ingest import readers
from bops.runtime import tiers

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_XLSX = os.path.join(REPO, "assets", "demo-data", "northwind_sales.xlsx")


def _candidate_interpreters():
    """Interpreters that might have openpyxl, without installing anything."""
    candidates = []
    managed = tiers.managed_python()
    if managed:
        candidates.append(managed)
    # A venv created during development; used only as a stand-in for the managed runtime.
    scratch = os.environ.get("BOPS_TEST_INTERPRETER")
    if scratch:
        candidates.append(scratch)
    if sys.executable:
        candidates.append(sys.executable)
    return [c for c in candidates if c and os.path.exists(c)]


def _interpreter_with_openpyxl():
    for interpreter in _candidate_interpreters():
        if interpreter == sys.executable:
            try:
                import openpyxl  # noqa: F401
                return interpreter
            except ImportError:
                continue
        if tiers.managed_has_openpyxl(interpreter):
            return interpreter
    return None


INTERPRETER = _interpreter_with_openpyxl()


@unittest.skipUnless(INTERPRETER,
                     "no interpreter with openpyxl available; Tier 2 cannot be exercised")
class TestTier2OutOfProcess(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dataset = readers.read_xlsx_managed(DEMO_XLSX, interpreter=INTERPRETER)

    def test_tier_2_is_recorded(self):
        self.assertEqual(self.dataset.reader_tier.tier, tiers.TIER_OPENPYXL_MANAGED)
        self.assertFalse(self.dataset.reader_tier.degraded)

    def test_interpreter_is_recorded_in_provenance(self):
        provenance = self.dataset.provenance()
        self.assertEqual(provenance["reader_tier"]["tier"], tiers.TIER_OPENPYXL_MANAGED)
        self.assertTrue(provenance["reader_tier"]["interpreter"])

    def test_data_is_read_correctly_across_the_process_boundary(self):
        self.assertEqual(self.dataset.row_count, 2204)
        self.assertEqual(self.dataset.column_count, 12)

    def test_types_survive_the_json_hop(self):
        import datetime
        row = self.dataset.rows[0]
        self.assertIsInstance(row["OrderDate"], datetime.date)
        self.assertIsInstance(row["NetRevenue"], float)
        self.assertIsInstance(row["Customer"], str)

    def test_tier2_agrees_with_tier3(self):
        tier3 = readers.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(self.dataset.row_count, tier3.row_count)
        self.assertEqual(self.dataset.columns, tier3.columns)
        for index in (0, 500, 1500, 2203):
            self.assertEqual(self.dataset.rows[index], tier3.rows[index],
                             "row %d differs between Tier 2 and Tier 3" % index)

    def test_managed_read_is_labelled(self):
        self.assertIn("tier2_managed_runtime", {w.code for w in self.dataset.warnings})


class TestTier2FailsSafely(unittest.TestCase):

    def test_absent_runtime_raises_rather_than_installing(self):
        from bops.errors import ConfigError
        with self.assertRaises(ConfigError):
            readers.read_xlsx_managed(DEMO_XLSX, interpreter="/definitely/not/here")

    def test_missing_file_raises_a_clear_error_not_a_raw_oserror(self):
        from bops.errors import ConfigError
        with self.assertRaises(ConfigError) as caught:
            readers.read_xlsx_managed("/no/such/file.xlsx", interpreter=sys.executable)
        self.assertIn("not found", str(caught.exception).lower())

    def test_subprocess_failure_is_reported_not_swallowed(self):
        from bops.errors import ConfigError
        # A real workbook, but an interpreter without openpyxl: the worker must fail and
        # the failure must surface rather than producing an empty dataset.
        try:
            import openpyxl  # noqa: F401
            self.skipTest("this interpreter has openpyxl, so the worker would succeed")
        except ImportError:
            pass
        with self.assertRaises(ConfigError) as caught:
            readers.read_xlsx_managed(DEMO_XLSX, interpreter=sys.executable)
        self.assertIn("managed runtime", str(caught.exception))


class TestNoSilentInstallation(unittest.TestCase):
    """The consent gate still holds now that Tier 2 is a real reading path."""

    def test_reading_never_triggers_a_bootstrap(self):
        calls = []
        original = tiers.bootstrap
        tiers.bootstrap = lambda *a, **k: calls.append(a)
        try:
            readers.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)
        finally:
            tiers.bootstrap = original
        self.assertEqual(calls, [], "reading must never install anything")

    def test_bootstrap_still_requires_consent(self):
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap()

    def test_bootstrap_writes_outside_the_repository(self):
        self.assertFalse(
            os.path.abspath(tiers.RUNTIME_DIR).startswith(REPO + os.sep))

    def test_worker_imports_nothing_that_could_install_or_spawn(self):
        """Checked against the parsed module, not its prose."""
        import ast

        worker = os.path.join(REPO, "lib", "python", "bops", "ingest", "_managed_read.py")
        self.assertTrue(os.path.exists(worker))
        tree = ast.parse(open(worker, encoding="utf-8").read())

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        for forbidden in ("subprocess", "pip", "os", "shutil", "urllib", "socket"):
            self.assertNotIn(forbidden, imported,
                             "the worker must not import %r" % forbidden)
        self.assertIn("json", imported)

    def test_worker_only_reads(self):
        import ast

        worker = os.path.join(REPO, "lib", "python", "bops", "ingest", "_managed_read.py")
        tree = ast.parse(open(worker, encoding="utf-8").read())
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertNotIn("open", called, "the worker must not open files for writing")
        self.assertNotIn("exec", called)
        self.assertNotIn("eval", called)


if __name__ == "__main__":
    unittest.main()
