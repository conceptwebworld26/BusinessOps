"""M13.1 large-dataset measurement - ADR-0039 section D.1 (M13-MEAS-D1).

Opt-in: skipped unless `BOPS_LARGE_DATASET=1`, following the `BOPS_AGENT_BOUNDARY_RUNTIME`
precedent, because generating and analysing 350,000 synthetic rows takes minutes.

    BOPS_LARGE_DATASET=1 python tests/run_tests.py integration.test_m13_large_dataset

Two deterministic synthetic CSV files - 100,000 and 250,000 rows - are generated into a
temporary directory (never committed) by `fixtures.build_m13_large_fixtures`. Each one is taken
through ingestion, the quality gate and the KPI engine (`pipeline.run`) and through one
analytics command (`/sales-analysis`).

**Correctness properties only are asserted:**

- the row count read equals the rows written;
- the processing mode is recorded honestly: a pass that is not complete is never presented
  as a full pass - it carries a global caveat naming its processing mode;
- the source file's SHA-256 is unchanged;
- no traceback (any exception fails the test);
- the revenue KPI equals the exact revenue total, which the fixture module computes
  independently of any reader.

**Measurement, never a threshold.** Elapsed time and the `tracemalloc` peak are recorded and
printed. There is no timing or memory pass/fail criterion, because no accepted architecture
defines one (ADR-0039 D.1). M3's always-on 60,000-row baseline in `test_performance.py` is
separate and is not edited. Large `.xlsx` is not measured: true chunked streaming is an open
Data Layer deferral (M3).

Elapsed time is measured in a pass with no allocation tracing; the memory peak comes from a
second pass under `tracemalloc`, so tracing overhead never inflates the recorded time.
"""

import atexit
import json
import os
import shutil
import sys
import tempfile
import time
import tracemalloc
import unittest

from bops import commands, pipeline
from bops.commands import runner
from bops.ingest import canonical as canonical_mod
from bops.kpi import contract as kpi_contract

from fixtures import build_m13_large_fixtures as large

ENABLED = os.environ.get("BOPS_LARGE_DATASET") == "1"
SIZES = (100000, 250000)

#: Filled by the tests, printed once at exit so test ordering cannot truncate the record.
MEASUREMENTS = []


def _print_measurements():
    if not MEASUREMENTS:
        return
    print(os.linesep + "  M13-MEAS-D1 (measurement, not benchmarking; no threshold)")
    for entry in MEASUREMENTS:
        print("  M13-MEAS-D1 " + json.dumps(entry, sort_keys=True))


atexit.register(_print_measurements)


def _peak_mib(peak_bytes):
    return round(peak_bytes / (1024.0 * 1024.0), 1)


@unittest.skipUnless(ENABLED, "large-dataset measurement is opt-in: BOPS_LARGE_DATASET=1")
class LargeDatasetMeasurement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-m13-large-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run_both(self, path):
        result = pipeline.run(path, load_context_files=False)
        command = commands.run("sales-analysis", path, load_context_files=False)
        return result, command

    def _measure(self, rows):
        start = time.perf_counter()
        path = large.large_csv(self.tmp, rows)
        generate_s = time.perf_counter() - start
        digest_before = runner.source_sha256(path)

        # Pass 1: elapsed time, no tracing.
        start = time.perf_counter()
        result = pipeline.run(path, load_context_files=False)
        pipeline_s = time.perf_counter() - start
        start = time.perf_counter()
        command = commands.run("sales-analysis", path, load_context_files=False)
        command_s = time.perf_counter() - start

        # Pass 2: traced allocation peak across the same two stages.
        tracemalloc.start()
        try:
            self._run_both(path)
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        digest_after = runner.source_sha256(path)
        canonical = result.canonical
        revenue = result.kpis.get("revenue")
        # `Ledger.summary()` holds the global caveats (`as_dict()` nests them under "summary").
        caveats = result.ledger.summary()["global_caveats"]
        entry = {
            "rows_written": rows,
            "file_bytes": os.path.getsize(path),
            "generate_s": round(generate_s, 2),
            "pipeline_s": round(pipeline_s, 2),
            "sales_analysis_s": round(command_s, 2),
            "tracemalloc_peak_mib": _peak_mib(peak),
            "row_count_read": result.dataset.row_count,
            "processing_mode": canonical.processing_mode,
            "rows_examined": canonical.rows_examined,
            "complete": canonical.complete,
            "large_row_threshold": canonical_mod.LARGE_ROW_THRESHOLD,
            "quality_grade": result.quality.grade if result.quality else None,
            "halted": result.halted,
            "revenue_status": revenue.status if revenue else None,
            "revenue_value": str(revenue.value) if revenue and revenue.value is not None
                             else None,
            "revenue_expected": large._pence(large.expected_revenue_pence(rows)),
            "global_caveats": caveats,
            "sales_analysis_status": command.status,
            "sha256_unchanged": digest_before == digest_after,
            "python": sys.version.split()[0],
        }
        MEASUREMENTS.append(entry)
        return result, command, entry, digest_before, digest_after

    def _assert_correctness(self, rows):
        result, command, entry, before, after = self._measure(rows)

        self.assertEqual(result.dataset.row_count, rows)
        self.assertEqual(result.canonical.row_count, rows)

        # Honesty: a pass that is not complete must say so; a complete one examined every row.
        canonical = result.canonical
        if canonical.complete:
            self.assertEqual(canonical.processing_mode, canonical_mod.FULL)
            self.assertEqual(canonical.rows_examined, rows)
        else:
            self.assertTrue(
                any(canonical.processing_mode in caveat for caveat in entry["global_caveats"]),
                "an incomplete pass carries no caveat naming its processing mode")

        self.assertEqual(before, after, "the source file changed")

        self.assertFalse(result.halted, result.halt_reason)
        revenue = result.kpis["revenue"]
        self.assertIn(revenue.status, (kpi_contract.COMPUTED, kpi_contract.PARTIAL))
        self.assertEqual(str(revenue.value), entry["revenue_expected"])

        self.assertEqual(command.status, runner.OK, command.reason)

    def test_100k_csv_rows(self):
        self._assert_correctness(100000)

    def test_250k_csv_rows(self):
        self._assert_correctness(250000)


class LargeFixtureDeterminism(unittest.TestCase):
    """Always on and cheap: the generator behind D.1 is byte-deterministic and synthetic."""

    def test_the_same_row_index_always_yields_the_same_row(self):
        self.assertEqual(large.row(12345), large.row(12345))
        self.assertEqual(len(large.row(0)), len(large.HEADERS))

    def test_two_generations_are_byte_identical(self):
        directory = tempfile.mkdtemp(prefix="bops-m13-det-")
        try:
            first = large.large_csv(directory, 2000, name="a.csv")
            second = large.large_csv(directory, 2000, name="b.csv")
            self.assertEqual(runner.source_sha256(first), runner.source_sha256(second))
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_the_expected_total_matches_the_written_file(self):
        directory = tempfile.mkdtemp(prefix="bops-m13-det-")
        try:
            path = large.large_csv(directory, 500)
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()[1:]
            written = sum(int(line.split(",")[9].replace(".", "")) for line in lines)
            self.assertEqual(written, large.expected_revenue_pence(500))
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_labels_are_obviously_synthetic(self):
        sample = large.row(7)
        self.assertTrue(sample[1].startswith("SYN-"))
        for value in (sample[2], sample[4], sample[5]):
            self.assertTrue(value.startswith("Synthetic "), value)
