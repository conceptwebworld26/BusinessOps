"""Configuration defaults and precedence resolution (architecture.md section 14)."""

import unittest

from bops import config
from bops.errors import ConfigError


class TestShippedDefaults(unittest.TestCase):
    def setUp(self):
        self.defaults = config.load_defaults()

    def test_all_architecture_sections_present(self):
        for section in ("locale", "materiality", "quality", "forecast",
                        "anomaly", "research", "runtime", "output"):
            self.assertIn(section, self.defaults)

    def test_approved_default_values(self):
        self.assertEqual(self.defaults["locale"]["currency"], "USD")
        self.assertEqual(self.defaults["locale"]["date_format"], "YYYY-MM-DD")
        self.assertEqual(self.defaults["materiality"]["absolute_amount"], 10000)
        self.assertEqual(self.defaults["materiality"]["percentage"], 5.0)
        self.assertEqual(self.defaults["forecast"]["min_history_periods"], 12)
        self.assertEqual(self.defaults["quality"]["halt_on"], "CRITICAL")
        self.assertEqual(self.defaults["research"]["disclosure"]["k_anonymity_floor"], 5)

    def test_bootstrap_default_asks(self):
        self.assertEqual(self.defaults["runtime"]["allow_bootstrap"], "ask")

    @staticmethod
    def _payload(mapping):
        """Config content with $-prefixed annotations stripped.

        Scanning must look at real keys and values, not at documentation comments —
        otherwise a comment saying "never put secrets here" trips the secret scan.
        """
        import json

        def strip(node):
            if isinstance(node, dict):
                return {k: strip(v) for k, v in node.items() if not k.startswith("$")}
            if isinstance(node, list):
                return [strip(v) for v in node]
            return node

        return json.dumps(strip(mapping)).lower()

    def test_no_secrets_in_defaults(self):
        blob = self._payload(self.defaults)
        for token in ("api_key", "apikey", "secret", "password", "credential",
                      "access_token", "bearer"):
            self.assertNotIn(token, blob)

    def test_no_business_specific_assumptions(self):
        # Defaults must be neutral: nothing naming an industry or business model.
        blob = self._payload(self.defaults)
        for token in ("saas", "retail", "consulting", "acme", "manufactur"):
            self.assertNotIn(token, blob)


class TestPrecedence(unittest.TestCase):
    """command argument -> project context -> user context -> shipped defaults."""

    def setUp(self):
        self.defaults = config.load_defaults()

    def test_defaults_only(self):
        resolved = config.resolve(defaults=self.defaults)
        self.assertEqual(resolved.get("locale.currency"), "USD")
        self.assertEqual(resolved.source_of("locale.currency"), "default")

    def test_user_context_overrides_default(self):
        resolved = config.resolve(
            defaults=self.defaults,
            user_context={"reporting": {"currency": "EUR"}})
        self.assertEqual(resolved.get("locale.currency"), "EUR")
        self.assertEqual(resolved.source_of("locale.currency"), "user")

    def test_project_context_overrides_user(self):
        resolved = config.resolve(
            defaults=self.defaults,
            user_context={"reporting": {"currency": "EUR"}},
            project_context={"reporting": {"currency": "GBP"}})
        self.assertEqual(resolved.get("locale.currency"), "GBP")
        self.assertEqual(resolved.source_of("locale.currency"), "project")

    def test_command_argument_overrides_everything(self):
        resolved = config.resolve(
            defaults=self.defaults,
            user_context={"reporting": {"currency": "EUR"}},
            project_context={"reporting": {"currency": "GBP"}},
            command_args={"locale": {"currency": "JPY"}})
        self.assertEqual(resolved.get("locale.currency"), "JPY")
        self.assertEqual(resolved.source_of("locale.currency"), "command")

    def test_full_four_layer_chain_in_one_resolution(self):
        resolved = config.resolve(
            defaults=self.defaults,
            user_context={"reporting": {"currency": "EUR", "date_format": "DD/MM/YYYY"}},
            project_context={"analysis": {"materiality": {"percentage": 2.5}}},
            command_args={"forecast": {"default_horizon_periods": 9}})
        self.assertEqual(resolved.get("locale.currency"), "EUR")            # user
        self.assertEqual(resolved.get("locale.date_format"), "DD/MM/YYYY")  # user
        self.assertEqual(resolved.get("materiality.percentage"), 2.5)       # project
        self.assertEqual(resolved.get("forecast.default_horizon_periods"), 9)  # command
        self.assertEqual(resolved.get("quality.halt_on"), "CRITICAL")       # default
        self.assertEqual(
            {resolved.source_of("locale.currency"),
             resolved.source_of("materiality.percentage"),
             resolved.source_of("forecast.default_horizon_periods"),
             resolved.source_of("quality.halt_on")},
            {"user", "project", "command", "default"})

    def test_unset_keys_keep_default_provenance(self):
        resolved = config.resolve(defaults=self.defaults,
                                  project_context={"reporting": {"currency": "GBP"}})
        self.assertEqual(resolved.source_of("materiality.absolute_amount"), "default")

    def test_materiality_override_from_context(self):
        resolved = config.resolve(
            defaults=self.defaults,
            project_context={"analysis": {"materiality": {"absolute_amount": 500,
                                                          "percentage": 1.0}}})
        self.assertEqual(resolved.get("materiality.absolute_amount"), 500)
        self.assertEqual(resolved.get("materiality.percentage"), 1.0)
        self.assertEqual(resolved.get("materiality.kpi_deviation"), 10.0)  # untouched

    def test_sources_used_reports_active_layers(self):
        resolved = config.resolve(defaults=self.defaults,
                                  command_args={"locale": {"currency": "CHF"}})
        self.assertEqual(resolved.sources_used(), ["command", "default"])

    def test_non_config_context_fields_do_not_leak(self):
        resolved = config.resolve(
            defaults=self.defaults,
            project_context={"identity": {"business_name": "Confidential Ltd"}})
        self.assertNotIn("Confidential Ltd", str(resolved.as_dict()))

    def test_get_returns_fallback_for_unknown_key(self):
        resolved = config.resolve(defaults=self.defaults)
        self.assertIsNone(resolved.get("nope.missing"))
        self.assertEqual(resolved.get("nope.missing", "fb"), "fb")

    def test_mutating_returned_dict_does_not_affect_config(self):
        resolved = config.resolve(defaults=self.defaults)
        snapshot = resolved.as_dict()
        snapshot["locale"]["currency"] = "MUTATED"
        self.assertEqual(resolved.get("locale.currency"), "USD")


class TestConfigFailures(unittest.TestCase):
    def test_missing_file_raises_config_error(self):
        with self.assertRaises(ConfigError):
            config.load_json("/definitely/not/here.json", "defaults")

    def test_invalid_json_raises_config_error(self):
        import os
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                fh.write("{ not json ")
            with self.assertRaises(ConfigError) as ctx:
                config.load_json(path, "defaults")
            self.assertIn("not valid JSON", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_schema_violation_raises(self):
        schema = {"type": "object",
                  "properties": {"locale": {"type": "object",
                                            "properties": {"currency": {"enum": ["USD"]}}}}}
        with self.assertRaises(ConfigError):
            config.resolve(defaults=config.load_defaults(),
                           command_args={"locale": {"currency": "XXX"}},
                           schema=schema)


if __name__ == "__main__":
    unittest.main()
