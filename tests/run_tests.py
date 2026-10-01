#!/usr/bin/env python3
"""BusinessOps test harness.

    python tests/run_tests.py              # everything
    python tests/run_tests.py -v           # verbose
    python tests/run_tests.py unit.test_config    # one module

Stdlib `unittest` only (ADR-0007): the correctness layer must run offline, free and
deterministically on any machine with Python, so that "never claim a test passed without
running it" is enforceable rather than aspirational.
"""

import os
import sys
import unittest

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
ENGINE_PATH = os.path.join(REPO_ROOT, "lib", "python")

for path in (ENGINE_PATH, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


def build_suite(pattern=None):
    loader = unittest.TestLoader()
    if pattern:
        return loader.loadTestsFromName(pattern)
    suite = unittest.TestSuite()
    for sub in ("unit", "integration", "negative"):
        directory = os.path.join(TESTS_DIR, sub)
        if os.path.isdir(directory):
            suite.addTests(loader.discover(directory, pattern="test_*.py",
                                           top_level_dir=TESTS_DIR))
    return suite


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    named = [a for a in argv if not a.startswith("-")]

    print("BusinessOps test suite")
    print("  python : %s" % sys.version.split()[0])
    print("  engine : %s" % ENGINE_PATH)
    print("-" * 68)

    suite = build_suite(named[0] if named else None)
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)

    print("-" * 68)
    print("ran %d | failures %d | errors %d | skipped %d"
          % (result.testsRun, len(result.failures), len(result.errors),
             len(result.skipped)))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
