import json
import unittest

from astrologically_intelligent.storage import Store
from astrologically_intelligent.tools import ToolRegistry


class ToolArgumentValidationTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.registry = ToolRegistry(self.store)

    def tearDown(self):
        self.registry.close()
        self.store.close()

    def test_rejects_unadvertised_fields_before_handler_runs(self):
        called = []
        self.registry.register(
            "test.strict", "Strict tool",
            {"type": "object", "properties": {"name": {"type": "string"}},
             "required": ["name"], "additionalProperties": False},
            lambda **kwargs: called.append(kwargs) or {"ok": True},
        )
        result = json.loads(self.registry.execute("test.strict", {"name": "valid", "admin": True}))
        self.assertIn("unsupported field", result["error"])
        self.assertEqual(called, [])

    def test_rejects_missing_required_fields(self):
        self.registry.register(
            "test.required", "Required tool",
            {"type": "object", "properties": {"name": {"type": "string"}},
             "required": ["name"], "additionalProperties": False},
            lambda name: {"name": name},
        )
        result = json.loads(self.registry.execute("test.required", {}))
        self.assertIn("missing required field", result["error"])

    def test_rejects_wrong_types_and_out_of_range_values(self):
        self.registry.register(
            "test.bounds", "Bounded tool",
            {"type": "object", "properties": {
                "count": {"type": "integer", "minimum": 1, "maximum": 3},
                "enabled": {"type": "boolean"},
            }, "required": ["count", "enabled"], "additionalProperties": False},
            lambda **kwargs: kwargs,
        )
        wrong_type = json.loads(self.registry.execute(
            "test.bounds", {"count": True, "enabled": True}))
        too_large = json.loads(self.registry.execute(
            "test.bounds", {"count": 4, "enabled": True}))
        self.assertIn("must be integer", wrong_type["error"])
        self.assertIn("minimum", too_large["error"]) if "minimum" in too_large["error"] else self.assertIn("maximum", too_large["error"])

    def test_accepts_valid_arguments(self):
        self.registry.register(
            "test.valid", "Valid tool",
            {"type": "object", "properties": {"name": {"type": "string", "minLength": 1}},
             "required": ["name"], "additionalProperties": False},
            lambda name: {"name": name},
        )
        result = json.loads(self.registry.execute("test.valid", {"name": "Astrologically Intelligent"}))
        self.assertEqual(result, {"name": "Astrologically Intelligent"})


if __name__ == "__main__":
    unittest.main()
