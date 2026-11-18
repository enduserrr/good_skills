"""Tests for decider_client — mocked transport, no live calls (live smoke is manual)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decider_client as dc  # noqa: E402


def _q():
    return {"approve": {"type": "choice", "instructions": "run without asking?",
                        "criteria": {"approve": "safe", "deny": "unsafe",
                                     "escalate": "unclear"}}}


SYSTEMONE_BODY = {
    "model": "/home/hermes/models/d1-2B-Q4_K_M.gguf",
    "answers": {"approve": {"type": "choice", "choice": "approve",
                            "probabilities": {"approve": 0.92, "deny": 0.01, "escalate": 0.07},
                            "confidence": 0.88}},
    "usage": {"input_tokens": 207, "output_tokens": 0},
}


class FakeTransport:
    """Stand-in for decider_client._http_post_json; records calls."""

    def __init__(self, body=None, exc=None, status_error=False):
        self.calls = []
        self.body = body
        self.exc = exc

    def __call__(self, url, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        if self.exc is not None:
            raise self.exc
        return self.body


def _fresh_cache():
    dc._CACHE.clear()


class TestRegistry(unittest.TestCase):
    def _registry_file(self, tmp, content):
        p = Path(tmp) / "models.json"
        p.write_text(json.dumps(content))
        return str(p)

    def test_default_model_resolves(self):
        reg = dc.load_registry()
        self.assertIn("default", reg)
        self.assertIn(reg["default"], reg["models"])

    def test_unknown_model_is_error_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            rp = self._registry_file(tmp, {"default": "a", "models": {
                "a": {"base_url": "http://x:1", "api": "systemone"}}})
            out = dc.ask("s", _q(), model="nope", registry_path=rp)
        self.assertFalse(out["ok"])
        self.assertNotIn("answers", out)

    def test_unknown_api_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rp = self._registry_file(tmp, {"default": "a", "models": {
                "a": {"base_url": "http://x:1", "api": "brainwave"}}})
            out = dc.ask("s", _q(), registry_path=rp)
        self.assertFalse(out["ok"])
        self.assertIn("api", out["error"].lower())


class TestSystemoneAdapter(unittest.TestCase):
    def test_payload_shape_and_url(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("state text", _q(), use_cache=False)
        self.assertTrue(out["ok"])
        self.assertEqual(fake.calls[0]["url"], "http://localhost:9931/v1/systemone")
        payload = fake.calls[0]["payload"]
        self.assertEqual(payload["state"], {"text": "state text"})
        self.assertIn("approve", payload["questions"])
        self.assertEqual(payload["questions"]["approve"]["type"], "choice")

    def test_normalized_answers(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("state text", _q(), use_cache=False)
        ans = out["answers"]["approve"]
        self.assertEqual(ans["choice"], "approve")
        self.assertAlmostEqual(ans["probabilities"]["approve"], 0.92)
        self.assertEqual(out["usage"]["output_tokens"], 0)

    def test_missing_answers_key_is_error(self):
        _fresh_cache()
        fake = FakeTransport(body={"model": "m"})
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", _q(), use_cache=False)
        self.assertFalse(out["ok"])
        self.assertNotIn("answers", out)


class TestFailureSemantics(unittest.TestCase):
    def test_transport_error_returns_error_dict(self):
        _fresh_cache()
        fake = FakeTransport(exc=ConnectionError("refused"))
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", _q(), use_cache=False)
        self.assertFalse(out["ok"])
        self.assertIn("refused", out["error"])
        self.assertNotIn("answers", out)

    def test_timeout_error_returns_error_dict(self):
        _fresh_cache()
        fake = FakeTransport(exc=TimeoutError("timed out"))
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", _q(), use_cache=False)
        self.assertFalse(out["ok"])

    def test_invalid_json_is_error(self):
        # adapter-level: transport returns non-dict garbage
        _fresh_cache()
        fake = FakeTransport(body="not json at all")
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", _q(), use_cache=False)
        self.assertFalse(out["ok"])


class TestQuestionsInput(unittest.TestCase):
    def test_list_form_normalized_by_name(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        qs = [{"name": "approve", "type": "choice", "instructions": "i",
               "criteria": {"approve": "safe", "deny": "unsafe", "escalate": "?"}}]
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", qs, use_cache=False)
        self.assertTrue(out["ok"])
        self.assertIn("approve", fake.calls[0]["payload"]["questions"])

    def test_list_missing_name_is_error(self):
        out = dc.ask("s", [{"type": "choice"}], registry_path="nonexistent-registry.json")
        self.assertFalse(out["ok"])

    def test_empty_questions_is_error(self):
        out = dc.ask("s", {}, registry_path="nonexistent-registry.json")
        self.assertFalse(out["ok"])

    def test_question_without_type_is_error(self):
        out = dc.ask("s", {"q1": {"instructions": "no type here"}},
                     registry_path="nonexistent-registry.json")
        self.assertFalse(out["ok"])


class TestCache(unittest.TestCase):
    def test_identical_call_hits_cache(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        with patch.object(dc, "_http_post_json", fake):
            first = dc.ask("same state", _q())
            second = dc.ask("same state", _q())
        self.assertEqual(len(fake.calls), 1)
        self.assertFalse(first.get("cached"))
        self.assertTrue(second.get("cached"))
        self.assertEqual(first["answers"], second["answers"])

    def test_use_cache_false_bypasses(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        with patch.object(dc, "_http_post_json", fake):
            dc.ask("same state", _q(), use_cache=False)
            dc.ask("same state", _q(), use_cache=False)
        self.assertEqual(len(fake.calls), 2)

    def test_different_state_misses(self):
        _fresh_cache()
        fake = FakeTransport(body=SYSTEMONE_BODY)
        with patch.object(dc, "_http_post_json", fake):
            dc.ask("state one", _q())
            dc.ask("state two", _q())
        self.assertEqual(len(fake.calls), 2)


class TestOpenAIChatAdapter(unittest.TestCase):
    CHAT_BODY = {"choices": [{"message": {"content": json.dumps({
        "answers": {"route": {"choice": "fetch_top3", "confidence": 0.7}}})}}]}

    def test_parses_json_content(self):
        _fresh_cache()
        fake = FakeTransport(body=self.CHAT_BODY)
        qs = {"route": {"type": "choice", "instructions": "which?",
                        "criteria": {"fetch_top3": "x", "fetch_all": "y"}}}
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", qs, model="future-chat-decider", use_cache=False,
                         registry_path=self._reg())
        self.assertTrue(out["ok"])
        self.assertIn("route", out["answers"])
        self.assertIn("/v1/chat/completions", fake.calls[0]["url"])

    def _reg(self):
        tmp = tempfile.mkdtemp()
        p = Path(tmp) / "models.json"
        p.write_text(json.dumps({"default": "future-chat-decider", "models": {
            "future-chat-decider": {"base_url": "http://localhost:9933",
                                    "api": "openai_chat"}}}))
        return str(p)

    def test_garbage_content_is_error(self):
        _fresh_cache()
        fake = FakeTransport(body={"choices": [{"message": {"content": "I feel like yes"}}]})
        qs = {"route": {"type": "choice", "instructions": "i",
                        "criteria": {"a": "x", "b": "y"}}}
        with patch.object(dc, "_http_post_json", fake):
            out = dc.ask("s", qs, model="future-chat-decider", use_cache=False,
                         registry_path=self._reg())
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
