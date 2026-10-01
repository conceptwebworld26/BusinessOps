# -*- coding: utf-8 -*-
"""M13-DEF-03, fixed in M14-5: the processing mode describes what actually happened.

Before the fix, `canonical.build()` chose the mode from the row count alone. A CSV of 100,001 rows
was read and computed in full, yet recorded as `streamed` and incomplete. Every figure then carried
"Only 100001 of 100001 rows were examined (streamed processing)", the revenue KPI was `partial`, and
the quality grade fell to WARNING on that finding alone. These tests run the defect record's own
reproducer at the threshold. The input is synthetic and deterministic, and it is written to a
temporary directory.
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO, "lib", "python"), os.path.join(REPO, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import pipeline                                                  # noqa: E402
from bops.ingest import canonical as canonical_mod                         # noqa: E402
from fixtures.build_m13_large_fixtures import large_csv                   # noqa: E402


class AboveTheThresholdAFullPassIsRecordedAsFull(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m14-5-mode-")
        cls.rows = canonical_mod.LARGE_ROW_THRESHOLD + 1
        cls.result = pipeline.run(large_csv(cls.directory, cls.rows), load_context_files=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def test_every_row_was_examined_and_the_pass_is_full_and_complete(self):
        canonical = self.result.canonical
        self.assertEqual(canonical.source.row_count, self.rows)
        self.assertEqual(canonical.rows_examined, self.rows)
        self.assertEqual(canonical.processing_mode, canonical_mod.FULL)
        self.assertTrue(canonical.complete)

    def test_no_caveat_claims_a_partial_pass(self):
        for caveat in self.result.ledger.summary()["global_caveats"]:
            self.assertNotIn("streamed processing", caveat)
            self.assertNotIn("examined portion", caveat)

    def test_revenue_is_not_marked_partial(self):
        self.assertNotEqual(self.result.kpis["revenue"].status, "partial")

    def test_a_caller_that_really_streamed_can_still_say_so(self):
        streamed = canonical_mod.build(self.result.canonical.source,
                                       processing_mode=canonical_mod.STREAMED)
        self.assertEqual(streamed.processing_mode, canonical_mod.STREAMED)
        self.assertFalse(streamed.complete)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
