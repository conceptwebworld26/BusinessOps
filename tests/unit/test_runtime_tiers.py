"""Reader tier resolution and the consent gate (ADR-0008, ADR-0010).

Every test injects probe results, so the suite never touches the network, never installs
anything, and gives the same answer on a machine with or without openpyxl.
"""

import os
import shutil
import tempfile
import unittest

from bops import runtime
from bops.errors import ConsentRequiredError, RuntimeUnavailableError
from bops.runtime import tiers


def probe(system=False, managed=False, bootstrap=False, stdlib=True, managed_path=None):
    return {
        "system_openpyxl": system,
        "managed_openpyxl": managed,
        "managed_python": managed_path or ("/fake/venv/bin/python" if managed else None),
        "bootstrap_possible": bootstrap,
        "stdlib_available": stdlib,
    }


class TestTierResolution(unittest.TestCase):
    def test_tier_1_when_openpyxl_importable(self):
        tier = tiers.resolve(_probe=probe(system=True))
        self.assertEqual(tier.tier, tiers.TIER_OPENPYXL_SYSTEM)
        self.assertFalse(tier.degraded)
        self.assertIsNone(tier.quality_warning())

    def test_tier_2_when_only_managed_runtime_has_it(self):
        tier = tiers.resolve(_probe=probe(managed=True))
        self.assertEqual(tier.tier, tiers.TIER_OPENPYXL_MANAGED)
        self.assertFalse(tier.degraded)

    def test_tier_1_preferred_over_tier_2(self):
        tier = tiers.resolve(_probe=probe(system=True, managed=True))
        self.assertEqual(tier.tier, tiers.TIER_OPENPYXL_SYSTEM)

    def test_tier_3_when_no_openpyxl_anywhere(self):
        tier = tiers.resolve(_probe=probe())
        self.assertEqual(tier.tier, tiers.TIER_STDLIB)
        self.assertTrue(tier.degraded)

    def test_tier_3_warning_describes_the_real_known_gap(self):
        warning = tiers.resolve(_probe=probe()).quality_warning()
        self.assertIn("Built-in number formats", warning)
        self.assertIn("refused rather than guessed", warning)

    def test_tier_4_when_no_python_reader_available(self):
        tier = tiers.resolve(_probe=probe(stdlib=False))
        self.assertEqual(tier.tier, tiers.TIER_CSV_FALLBACK)
        self.assertTrue(tier.degraded)
        self.assertIn("export the sheet to CSV", tier.quality_warning())

    def test_tier_3_advertises_possible_upgrade(self):
        tier = tiers.resolve(_probe=probe(bootstrap=True))
        self.assertTrue(tier.bootstrap_available)
        self.assertIn("consented Tier 2 bootstrap", tier.reason)

    def test_allow_bootstrap_never_suppresses_the_offer(self):
        tier = tiers.resolve(allow_bootstrap="never", _probe=probe(bootstrap=True))
        self.assertFalse(tier.bootstrap_available)
        self.assertNotIn("bootstrap", tier.reason)

    def test_prefer_pins_a_tier(self):
        tier = tiers.resolve(prefer=tiers.TIER_STDLIB, _probe=probe(system=True))
        self.assertEqual(tier.tier, tiers.TIER_STDLIB)

    def test_prefer_unavailable_tier_raises(self):
        with self.assertRaises(RuntimeUnavailableError):
            tiers.resolve(prefer=tiers.TIER_OPENPYXL_SYSTEM, _probe=probe())


class TestTierRecording(unittest.TestCase):
    """The chosen tier must be recordable on every dataset (ADR-0008)."""

    def test_as_dict_carries_provenance(self):
        record = tiers.resolve(_probe=probe(system=True)).as_dict()
        for key in ("tier", "name", "reason", "interpreter", "degraded"):
            self.assertIn(key, record)
        self.assertEqual(record["tier"], 1)

    def test_record_is_json_serialisable(self):
        import json
        json.dumps(tiers.resolve(_probe=probe()).as_dict())

    def test_state_round_trips_outside_the_repo(self):
        tmp = tempfile.mkdtemp()
        try:
            tier = tiers.resolve(_probe=probe(system=True))
            path = tiers.write_state(tier, tmp)
            self.assertTrue(os.path.exists(path))
            state = tiers.read_state(tmp)
            self.assertEqual(state["tier"], 1)
            self.assertEqual(state["pin"], tiers.OPENPYXL_PIN)
        finally:
            shutil.rmtree(tmp)

    def test_read_state_absent_returns_none(self):
        tmp = tempfile.mkdtemp()
        try:
            self.assertIsNone(tiers.read_state(tmp))
        finally:
            shutil.rmtree(tmp)


class TestConsentGate(unittest.TestCase):
    """No silent installation, ever."""

    def test_resolution_never_installs(self):
        calls = []

        def spy(argv):
            calls.append(argv)

        tiers.resolve(_probe=probe(bootstrap=True))
        self.assertEqual(calls, [], "resolve() must never run a command")

    def test_bootstrap_without_consent_raises(self):
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap(consent=False)

    def test_bootstrap_default_is_no_consent(self):
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap()

    def test_bootstrap_runs_nothing_when_consent_withheld(self):
        calls = []
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap(consent=False, _runner=lambda argv: calls.append(argv))
        self.assertEqual(calls, [], "no command may run without consent")

    def test_truthy_is_not_consent(self):
        # Only the literal True counts, so a stray truthy value cannot authorise an install.
        for sneaky in (1, "yes", ["ok"], {"consent": True}):
            with self.assertRaises(ConsentRequiredError):
                tiers.bootstrap(consent=sneaky)

    def test_allow_bootstrap_never_blocks_even_with_consent(self):
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap(consent=True, allow_bootstrap="never")

    def test_no_config_value_can_pre_authorise(self):
        # ADR-0010: approval is per-action and non-transferable, so "always" is not a
        # supported setting — it must still demand explicit consent.
        with self.assertRaises(ConsentRequiredError):
            tiers.bootstrap(consent=False, allow_bootstrap="always")

    def test_consent_request_discloses_what_and_where(self):
        request = tiers.consent_request()
        self.assertEqual(request["package"], tiers.OPENPYXL_PIN)
        self.assertIn("businessops", request["location"].lower())
        self.assertFalse(request["touches_system_python"])
        self.assertFalse(request["touches_repository"])
        self.assertIn("Tier 3", request["if_declined"])
        self.assertIn("delete", request["reversible"])

    def test_consent_request_absent_when_bootstrap_disabled(self):
        self.assertIsNone(tiers.consent_request(allow_bootstrap="never"))

    def test_error_message_states_what_is_being_asked(self):
        with self.assertRaises(ConsentRequiredError) as caught:
            tiers.bootstrap(consent=False)
        message = str(caught.exception)
        self.assertIn(tiers.OPENPYXL_PIN, message)
        self.assertIn("undo", message)


class TestPinning(unittest.TestCase):
    def test_version_is_pinned_exactly(self):
        self.assertEqual(tiers.OPENPYXL_PIN, "openpyxl==3.1.5")
        self.assertIn("==", tiers.OPENPYXL_PIN)

    def test_bootstrap_installs_the_pinned_version(self):
        calls = []
        tmp = tempfile.mkdtemp()
        try:
            interpreter = os.path.join(tmp, "bin", "python")
            os.makedirs(os.path.dirname(interpreter))
            with open(interpreter, "w") as fh:
                fh.write("")
            tiers.bootstrap(consent=True, runtime_dir=tmp,
                            _runner=lambda argv: calls.append(argv))
            install = [c for c in calls if "install" in c]
            self.assertEqual(len(install), 1)
            self.assertIn(tiers.OPENPYXL_PIN, install[0])
        finally:
            shutil.rmtree(tmp)

    def test_bootstrap_targets_isolated_dir_not_system_python(self):
        calls = []
        tmp = tempfile.mkdtemp()
        try:
            interpreter = os.path.join(tmp, "bin", "python")
            os.makedirs(os.path.dirname(interpreter))
            with open(interpreter, "w") as fh:
                fh.write("")
            tiers.bootstrap(consent=True, runtime_dir=tmp,
                            _runner=lambda argv: calls.append(argv))
            venv_call = [c for c in calls if "venv" in c][0]
            self.assertIn(tmp, venv_call)
            install = [c for c in calls if "install" in c][0]
            self.assertTrue(install[0].startswith(tmp),
                            "must install with the managed interpreter, not the system one")
        finally:
            shutil.rmtree(tmp)


class TestModuleSurface(unittest.TestCase):
    def test_public_api_exported(self):
        for name in ("resolve", "bootstrap", "consent_request", "ReaderTier",
                     "OPENPYXL_PIN", "RUNTIME_DIR"):
            self.assertTrue(hasattr(runtime, name), name)

    def test_runtime_dir_is_under_user_home_not_repo(self):
        self.assertIn(".claude", tiers.RUNTIME_DIR)
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.assertFalse(os.path.abspath(tiers.RUNTIME_DIR).startswith(repo + os.sep))


if __name__ == "__main__":
    unittest.main()
