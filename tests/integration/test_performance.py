"""Performance baseline for the data layer (M3 §16).

Measurement, not benchmarking. The point is to know what ingestion costs today so a future
regression is visible, and to prove the large-file path records its processing mode honestly
rather than presenting a sample as a full pass.

Thresholds are deliberately loose — they exist to catch an order-of-magnitude regression,
not to police a few milliseconds on a busy machine.
"""

import atexit
import os
import shutil
import tempfile
import time
import unittest

from bops import ingest
from bops.ingest import canonical as canonical_mod
from bops.runtime import tiers

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_CSV = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_XLSX = os.path.join(REPO, "assets", "demo-data", "northwind_sales.xlsx")

MEASUREMENTS = []


def _print_baseline():
    """Printed at exit so the order test classes run in cannot truncate the table."""
    if not MEASUREMENTS:
        return
    print(os.linesep + "  baseline (measurement, not benchmarking)")
    for label, elapsed, subject, unit in MEASUREMENTS:
        if unit is not None:
            # A run that returns metrics or findings has no meaningful rows/s figure.
            count, name = unit
            print("    %-36s %7d %-8s %6.2fs" % (label, count, name, elapsed))
            continue
        rows = getattr(subject, "row_count", getattr(subject, "rows_checked", None))
        if rows is None:
            print("    %-36s %7d metrics  %6.2fs" % (label, len(subject), elapsed))
            continue
        rate = int(rows / elapsed) if elapsed > 0 else 0
        print("    %-36s %7d rows  %6.2fs  %8d rows/s" % (label, rows, elapsed, rate))


atexit.register(_print_baseline)


def measure(label, fn, unit=None):
    """`unit` is an explicit (count, name) pair for results that are not rows."""
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    MEASUREMENTS.append((label, elapsed, result, unit(result) if unit else None))
    return result, elapsed


def build_large_csv(directory, rows=60000, name="large.csv"):
    """A dataset an order of magnitude larger than the demo."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("OrderDate,OrderID,Region,Product,Quantity,NetRevenue,CostOfGoods\n")
        for index in range(rows):
            month = (index % 24) + 1
            fh.write("2025-%02d-15,SO-%06d,R%d,P%d,%d,%.2f,%.2f\n"
                     % ((month - 1) % 12 + 1, index, index % 4, index % 6,
                        (index % 9) + 1, 100.0 + (index % 500), 60.0 + (index % 300)))
    return path


class TestPerformanceBaseline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-")

    @classmethod
    def tearDownClass(cls):
        # The baseline table is printed once, at exit, by `_print_baseline`; a
        # partial table here would show only whichever rows exist by now.
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_demo_csv_baseline(self):
        dataset, elapsed = measure("demo CSV (2.2k rows)",
                                   lambda: ingest.read_csv(DEMO_CSV))
        self.assertEqual(dataset.row_count, 2204)
        self.assertLess(elapsed, 10.0)

    def test_demo_xlsx_tier3_baseline(self):
        dataset, elapsed = measure(
            "demo XLSX tier 3 (2.2k rows)",
            lambda: ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB))
        self.assertEqual(dataset.row_count, 2204)
        self.assertLess(elapsed, 20.0)

    def test_canonical_build_baseline(self):
        dataset = ingest.read_csv(DEMO_CSV)
        _canonical, elapsed = measure("canonical build (2.2k rows)",
                                      lambda: canonical_mod.build(dataset))
        self.assertLess(elapsed, 20.0)

    def test_large_csv_baseline(self):
        path = build_large_csv(self.tmp)
        dataset, elapsed = measure("large CSV (60k rows)",
                                   lambda: ingest.read_csv(path))
        self.assertEqual(dataset.row_count, 60000)
        self.assertLess(elapsed, 60.0)

    def test_large_canonical_build_baseline(self):
        path = build_large_csv(self.tmp, rows=60000, name="large2.csv")
        dataset = ingest.read_csv(path)
        canonical, elapsed = measure("canonical build (60k rows)",
                                     lambda: canonical_mod.build(dataset))
        self.assertLess(elapsed, 60.0)
        # Profiling samples; the row count is still complete because every row was read.
        self.assertEqual(canonical.row_count, 60000)


class TestQualityPerformanceBaseline(unittest.TestCase):
    """What the thirteen-family quality pass costs. Measurement, not benchmarking."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-q-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _quality(self, path):
        from bops import config as config_mod
        from bops import mapping as mapping_mod
        from bops.quality import checks as quality_checks
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset)
        semantic_map = mapping_mod.infer(dataset)
        config = config_mod.resolve(defaults=config_mod.load_defaults())
        return lambda: quality_checks.run(dataset, semantic_map, config, canonical)

    def test_quality_pass_on_demo_dataset(self):
        report, elapsed = measure("quality: 13 families (2.2k rows)",
                                  self._quality(DEMO_CSV))
        self.assertEqual(report.rows_checked, 2204)
        self.assertLess(elapsed, 30.0)

    def test_quality_pass_on_large_dataset(self):
        path = build_large_csv(self.tmp, rows=30000, name="large_quality.csv")
        report, elapsed = measure("quality: 13 families (30k rows)",
                                  self._quality(path))
        self.assertEqual(report.rows_checked, 30000)
        self.assertLess(elapsed, 90.0)


class TestKpiPerformanceBaseline(unittest.TestCase):
    """What the 28-metric catalogue costs. Measurement, not benchmarking."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-kpi-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _kpis(self, path):
        from bops import config as config_mod
        from bops import kpi, mapping
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset)
        semantic_map = mapping.infer(dataset)
        config = config_mod.resolve(defaults=config_mod.load_defaults())
        return lambda: kpi.calculate(dataset, semantic_map, None, config,
                                     canonical=canonical)

    def test_full_catalogue_on_demo_dataset(self):
        results, elapsed = measure("kpi: 28 metrics (2.2k rows)", self._kpis(DEMO_CSV))
        self.assertEqual(len(results), 28)
        self.assertLess(elapsed, 60.0)

    def test_full_catalogue_on_multi_period_dataset(self):
        import sys
        sys.path.insert(0, os.path.join(REPO, "tests"))
        from fixtures import build_kpi_fixtures as fx
        path = fx.rich_business(self.tmp, months=24, per_month=20)
        results, elapsed = measure("kpi: 28 metrics (480 rows, 24 periods)",
                                   self._kpis(path))
        self.assertEqual(len(results), 28)
        self.assertLess(elapsed, 60.0)

    def test_full_catalogue_on_larger_dataset(self):
        path = build_large_csv(self.tmp, rows=30000, name="large_kpi.csv")
        results, elapsed = measure("kpi: 28 metrics (30k rows)", self._kpis(path))
        self.assertEqual(len(results), 28)
        self.assertLess(elapsed, 120.0)


class TestAnalyticsBaseline(unittest.TestCase):
    """What the four analytical domains cost on top of ingestion, quality and KPIs."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-analytics-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _analytics(self, path):
        from bops import analytics, pipeline
        result = pipeline.run(path, load_context_files=False)
        return lambda: analytics.analyse_all(result)

    @staticmethod
    def _findings(sets):
        return (sum(len(a.findings) for a in sets.values()), "findings")

    def test_all_domains_on_demo_dataset(self):
        sets, elapsed = measure("analytics: 4 domains (2.2k rows)",
                                self._analytics(DEMO_CSV), unit=self._findings)
        self.assertEqual(len(sets), 4)
        self.assertLess(elapsed, 60.0)

    def test_all_domains_on_larger_dataset(self):
        path = build_large_csv(self.tmp, rows=30000, name="large_analytics.csv")
        sets, elapsed = measure("analytics: 4 domains (30k rows)",
                                self._analytics(path), unit=self._findings)
        self.assertEqual(len(sets), 4)
        self.assertLess(elapsed, 120.0)

    def test_segmentation_primitive_on_larger_dataset(self):
        from bops import mapping
        from bops.analytics import segmentation
        path = build_large_csv(self.tmp, rows=30000, name="large_segment.csv")
        dataset = ingest.read(path)
        semantic_map = mapping.infer(dataset)
        segments, elapsed = measure(
            "segmentation: by product (30k rows)",
            lambda: segmentation.segment(dataset, semantic_map, mapping.PRODUCT),
            unit=lambda s: (len(s), "segments"))
        self.assertTrue(segments)
        self.assertLess(elapsed, 60.0)


class TestForecastAndAnomalyBaseline(unittest.TestCase):
    """What the Milestone 8 engines cost on top of a completed pipeline run.

    Measured separately from the commands because both are optional passes: a caller that
    never asks for a forecast never pays for one, and the numbers should show what asking
    actually costs.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-m8-")
        cls.large = build_large_csv(cls.tmp, rows=30000, name="large_m8.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _result(self, path):
        from bops import pipeline
        return pipeline.run(path, load_context_files=False)

    def test_forecast_on_demo_dataset(self):
        from bops import pipeline
        result = self._result(DEMO_CSV)
        forecasts, elapsed = measure(
            "forecast: 4 targets (2.2k rows, 24 periods)",
            lambda: pipeline.forecast(result),
            unit=lambda f: (len(f.available_forecasts()), "forecasts"))
        self.assertTrue(forecasts.forecasts)
        self.assertLess(elapsed, 60.0)

    def test_forecast_on_larger_dataset(self):
        from bops import pipeline
        result = self._result(self.large)
        _forecasts, elapsed = measure(
            "forecast: 4 targets (30k rows)",
            lambda: pipeline.forecast(result),
            unit=lambda f: (len(f.available_forecasts()), "forecasts"))
        self.assertLess(elapsed, 120.0)

    def test_anomaly_scan_on_demo_dataset(self):
        from bops import pipeline
        result = self._result(DEMO_CSV)
        scan, elapsed = measure(
            "anomaly: 8 metrics (2.2k rows, 24 periods)",
            lambda: pipeline.detect_anomalies(result),
            unit=lambda s: (len(s.observations), "periods checked"))
        self.assertTrue(scan.observations)
        self.assertLess(elapsed, 60.0)

    def test_anomaly_scan_on_larger_dataset(self):
        from bops import pipeline
        result = self._result(self.large)
        _scan, elapsed = measure(
            "anomaly: 8 metrics (30k rows)",
            lambda: pipeline.detect_anomalies(result),
            unit=lambda s: (len(s.observations), "periods checked"))
        self.assertLess(elapsed, 120.0)

    def test_backtest_selection_cost_in_isolation(self):
        """Method selection backtests every adequate method, so it is measured alone."""
        from bops import mapping, pipeline
        from bops.forecast import series as series_mod, validate
        result = self._result(DEMO_CSV)
        history, _reason = series_mod.prepare(
            result.dataset, result.semantic_map, mapping.REVENUE, "Revenue")
        chosen, _validation, _scored = measure(
            "forecast: backtest 5 methods (24 periods)",
            lambda: validate.select(history, 6),
            unit=lambda outcome: (len(outcome[2]), "candidates scored"))[0]
        self.assertIsNotNone(chosen)


class TestCommandBaseline(unittest.TestCase):
    """What each user-facing command costs end to end, including rendering."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-perf-commands-")
        cls.large = build_large_csv(cls.tmp, rows=30000, name="large_commands.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @staticmethod
    def _sections(rendered):
        return (rendered.count("\n## "), "sections")

    def _command(self, command_id, path, question=None):
        from bops import commands

        def call():
            run = commands.run(command_id, path, question=question,
                               load_context_files=False)
            return commands.render(run)
        return call

    def test_every_command_on_the_demo_dataset(self):
        from bops import commands
        for command_id in commands.COMMAND_IDS:
            question = ("Which region grew fastest?"
                        if command_id == "ask-business-data" else None)
            rendered, elapsed = measure(
                "command: /%s (2.2k rows)" % command_id,
                self._command(command_id, DEMO_CSV, question), unit=self._sections)
            self.assertTrue(rendered)
            self.assertLess(elapsed, 60.0)

    def test_the_two_heaviest_commands_on_a_larger_dataset(self):
        for command_id in ("business-health", "sales-analysis"):
            rendered, elapsed = measure(
                "command: /%s (30k rows)" % command_id,
                self._command(command_id, self.large), unit=self._sections)
            self.assertTrue(rendered)
            self.assertLess(elapsed, 120.0)


class TestProcessingModeHonesty(unittest.TestCase):
    """A sampled or streamed pass must never be presented as a full one."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-perf-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ordinary_dataset_is_full_mode(self):
        canonical = canonical_mod.build(ingest.read_csv(DEMO_CSV))
        self.assertEqual(canonical.processing_mode, canonical_mod.FULL)
        self.assertTrue(canonical.complete)

    def test_large_dataset_is_marked_streamed(self):
        dataset = ingest.read_csv(build_large_csv(self.tmp, rows=100))
        # Force the large-file decision without building a 100k-row file.
        canonical = canonical_mod.build(
            dataset, processing_mode=canonical_mod.STREAMED)
        self.assertEqual(canonical.processing_mode, canonical_mod.STREAMED)
        self.assertIn("processing_mode", canonical.provenance())

    def test_threshold_selects_streaming(self):
        self.assertGreater(canonical_mod.LARGE_ROW_THRESHOLD, 0)
        dataset = ingest.read_csv(build_large_csv(self.tmp, rows=10))
        dataset.rows = dataset.rows * 1          # small: stays full
        self.assertEqual(canonical_mod.build(dataset).processing_mode,
                         canonical_mod.FULL)

    def test_sampled_mode_is_reported_as_incomplete(self):
        dataset = ingest.read_csv(DEMO_CSV)
        canonical = canonical_mod.CanonicalDataset(
            dataset, [], processing_mode=canonical_mod.SAMPLED, rows_examined=100)
        self.assertFalse(canonical.complete)
        self.assertEqual(canonical.provenance()["rows_examined"], 100)
        self.assertFalse(canonical.provenance()["complete"])

    def test_incomplete_pass_adds_a_global_caveat_to_the_ledger(self):
        from bops import pipeline
        original = canonical_mod.build

        def sampled_build(dataset, **kwargs):
            kwargs["processing_mode"] = canonical_mod.SAMPLED
            kwargs["rows_examined"] = 100
            return original(dataset, **kwargs)

        canonical_mod.build = sampled_build
        try:
            result = pipeline.run(DEMO_CSV, load_context_files=False)
        finally:
            canonical_mod.build = original

        caveats = result.ledger.summary()["global_caveats"]
        self.assertTrue(any("Only 100" in c for c in caveats),
                        "an incomplete pass must be disclosed on every claim")


if __name__ == "__main__":
    unittest.main()
