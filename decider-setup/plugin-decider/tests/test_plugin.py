"""Plugin-contract test: package imports like the loader would, register(ctx)
exposes exactly one 'decide' tool, and its handler honors the failure contract."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_plugin():
    sys.path.insert(0, str(PLUGIN_DIR))
    spec = importlib.util.spec_from_file_location(
        "decider_pkg", PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)])
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # required for relative imports during exec
    spec.loader.exec_module(mod)
    return mod


class FakeCtx:
    def __init__(self):
        self.registered = {}

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.registered[name] = {"toolset": toolset, "schema": schema,
                                 "handler": handler, **kwargs}


SYSTEMONE_BODY = {"answers": {"q1": {"type": "choice", "choice": "a",
                                     "probabilities": {"a": 0.9}, "confidence": 0.8}},
                  "usage": {"input_tokens": 10, "output_tokens": 0}}


class TestPluginContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_plugin()
        cls.ctx = FakeCtx()
        cls.mod.register(cls.ctx)

    def test_registers_decide_tool(self):
        self.assertIn("decide", self.ctx.registered)
        self.assertEqual(self.ctx.registered["decide"]["toolset"], "decider")

    def test_schema_requires_state_and_questions(self):
        params = self.ctx.registered["decide"]["schema"]["parameters"]
        self.assertEqual(params["required"], ["state_context", "questions"])
        q = params["properties"]["questions"]["items"]
        self.assertEqual(q["required"], ["name", "type", "instructions"])

    def test_check_fn_present(self):
        self.assertIsNotNone(self.ctx.registered["decide"].get("check_fn"))

    def test_handler_success_returns_json_string(self):
        handler = self.ctx.registered["decide"]["handler"]
        with patch.object(self.mod.decider_client, "_http_post_json",
                          return_value=SYSTEMONE_BODY):
            out = json.loads(handler({"state_context": "s",
                                      "questions": [{"name": "q1",
                                                     "type": "choice",
                                                     "instructions": "i"}]}))
        self.assertTrue(out["ok"])
        self.assertIn("q1", out["answers"])

    def test_handler_failure_contract(self):
        handler = self.ctx.registered["decide"]["handler"]
        out = json.loads(handler({"state_context": "s",
                                  "questions": [{"name": "q1", "type": "choice",
                                                 "instructions": "i"}],
                                  "model": "does-not-exist"}))
        self.assertFalse(out["ok"])
        self.assertNotIn("answers", out)


if __name__ == "__main__":
    unittest.main()
