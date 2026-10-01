"""The stdlib JSON Schema subset validator.

This module underpins config and Business Context validation, so its own correctness —
especially its *rejections* — needs direct coverage.
"""

import unittest

from bops import jsonschema_mini as js
from bops.context import loader


class TestTypes(unittest.TestCase):
    def test_accepts_correct_types(self):
        for value, kind in (("s", "string"), (1, "integer"), (1.5, "number"),
                            (True, "boolean"), ([], "array"), ({}, "object"), (None, "null")):
            self.assertEqual(js.validate(value, {"type": kind}), [], kind)

    def test_rejects_wrong_type(self):
        self.assertTrue(js.validate("nope", {"type": "integer"}))

    def test_bool_is_not_a_number(self):
        # JSON Schema treats them as distinct even though Python does not.
        self.assertTrue(js.validate(True, {"type": "integer"}))
        self.assertTrue(js.validate(False, {"type": "number"}))

    def test_integer_accepted_as_number(self):
        self.assertEqual(js.validate(5, {"type": "number"}), [])

    def test_union_type(self):
        schema = {"type": ["string", "null"]}
        self.assertEqual(js.validate("x", schema), [])
        self.assertEqual(js.validate(None, schema), [])
        self.assertTrue(js.validate(3, schema))


class TestConstraints(unittest.TestCase):
    def test_required(self):
        errors = js.validate({}, {"type": "object", "required": ["a"]})
        self.assertIn("missing required property", str(errors[0]))

    def test_enum(self):
        self.assertTrue(js.validate("d", {"enum": ["a", "b"]}))
        self.assertEqual(js.validate("a", {"enum": ["a", "b"]}), [])

    def test_bounds(self):
        self.assertTrue(js.validate(5, {"minimum": 10}))
        self.assertTrue(js.validate(50, {"maximum": 10}))
        self.assertEqual(js.validate(10, {"minimum": 10, "maximum": 10}), [])

    def test_string_length_and_pattern(self):
        self.assertTrue(js.validate("", {"minLength": 1}))
        self.assertTrue(js.validate("toolong", {"maxLength": 3}))
        self.assertTrue(js.validate("gbp", {"pattern": "^[A-Z]{3}$"}))
        self.assertEqual(js.validate("GBP", {"pattern": "^[A-Z]{3}$"}), [])

    def test_additional_properties_false(self):
        schema = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
        self.assertTrue(js.validate({"b": 1}, schema))
        self.assertEqual(js.validate({"a": 1}, schema), [])

    def test_additional_properties_schema_applied(self):
        schema = {"type": "object", "additionalProperties": {"type": "string"}}
        self.assertTrue(js.validate({"x": 5}, schema))
        self.assertEqual(js.validate({"x": "ok"}, schema), [])

    def test_array_items_and_bounds(self):
        schema = {"type": "array", "items": {"type": "string"}, "maxItems": 2}
        self.assertTrue(js.validate(["a", 1], schema))
        self.assertTrue(js.validate(["a", "b", "c"], schema))
        self.assertEqual(js.validate(["a"], schema), [])

    def test_nested_error_paths_locate_the_problem(self):
        schema = {"type": "object", "properties": {
            "outer": {"type": "object", "properties": {"inner": {"type": "integer"}}}}}
        errors = js.validate({"outer": {"inner": "bad"}}, schema)
        self.assertEqual(errors[0].path, "outer.inner")

    def test_collects_all_errors_not_just_the_first(self):
        schema = {"type": "object", "required": ["a", "b", "c"]}
        self.assertEqual(len(js.validate({}, schema)), 3)


class TestUnsupportedKeywordGuard(unittest.TestCase):
    """A schema must not silently lose enforcement."""

    def test_detects_unknown_keyword(self):
        found = js.unsupported_keywords({"type": "string", "multipleOf": 2})
        self.assertIn("multipleOf", found)

    def test_annotations_are_not_flagged(self):
        found = js.unsupported_keywords(
            {"type": "string", "title": "t", "description": "d", "$comment": "c"})
        self.assertEqual(found, set())

    def test_x_annotations_are_not_flagged(self):
        found = js.unsupported_keywords({"type": "string", "x-privacy": "public"})
        self.assertEqual(found, set())

    def test_business_context_schema_uses_only_supported_keywords(self):
        # If this fails, the schema gained a keyword the validator silently ignores.
        self.assertEqual(js.unsupported_keywords(loader.load_schema()), set())


if __name__ == "__main__":
    unittest.main()
