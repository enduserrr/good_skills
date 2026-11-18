"""Shim tests — decider mocked at decider_client.ask; no sockets."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import guardian_shim as shim  # noqa: E402


def _ans(choice, p, conf=0.9):
    return {"type": "choice", "choice": choice, "confidence": conf,
            "probabilities": {choice: p, **{c: (1 - p) / 2 for c in
                                            ("approve", "deny", "escalate") if c != choice}}}


GUARDIAN_BODY = {
    "messages": [
        {"role": "system", "content": "You are a security reviewer..."},
        {"role": "user", "content": (
            "The following command was flagged as: script execution via -c flag\n\n"
            "<command>\npython3 -c 'print(1+1)'\n</command>\n\n"
            "Assess the ACTUAL risk... Respond with exactly one word: APPROVE, DENY, or ESCALATE")},
    ]
}


class TestParse(unittest.TestCase):
    def test_realistic_guardian_prompt(self):
        cmd, desc = shim.parse_guardian_prompt(GUARDIAN_BODY["messages"])
        self.assertEqual(cmd, "python3 -c 'print(1+1)'")
        self.assertEqual(desc, "script execution via -c flag")

    def test_missing_command_block(self):
        cmd, desc = shim.parse_guardian_prompt([{"role": "user",
                                                 "content": "no delimiters here"}])
        self.assertEqual(cmd, "")

    def test_empty_messages(self):
        cmd, _ = shim.parse_guardian_prompt([])
        self.assertEqual(cmd, "")


class TestVerdictRules(unittest.TestCase):
    def test_strong_approve(self):
        v, _ = shim._verdict_from_answer(_ans("approve", 0.95, 0.8))
        self.assertEqual(v, "APPROVE")

    def test_low_confidence_escalates(self):
        v, _ = shim._verdict_from_answer(_ans("approve", 0.95, 0.5))
        self.assertEqual(v, "ESCALATE")

    def test_below_threshold_escalates(self):
        v, _ = shim._verdict_from_answer(_ans("approve", 0.80, 0.9))
        self.assertEqual(v, "ESCALATE")

    def test_strong_deny(self):
        v, _ = shim._verdict_from_answer(_ans("deny", 0.90))
        self.assertEqual(v, "DENY")

    def test_weak_deny_escalates(self):
        v, _ = shim._verdict_from_answer(_ans("deny", 0.60))
        self.assertEqual(v, "ESCALATE")


class TestHighImpact(unittest.TestCase):
    def test_regex_matches_destructive_classes(self):
        for cmd in ("mkfs.ext4 /dev/sda1", "rm -rf ~/models", "git push --force origin main",
                    "shutdown -h now", "dd if=/dev/zero of=/dev/sda", "systemctl restart nginx"):
            self.assertTrue(shim.HIGH_IMPACT.search(cmd), cmd)

    def test_benign_not_matched(self):
        for cmd in ("grep -rn foo src/", "systemctl --user restart app", "git status",
                    "pip install --user requests"):
            self.assertIsNone(shim.HIGH_IMPACT.search(cmd), cmd)

    def test_unanimous_approve_required(self):
        votes = {"vote0": _ans("approve", 0.99), "vote1": _ans("approve", 0.97),
                 "vote2": _ans("approve", 0.95)}
        v, info = shim._ensemble_verdict(votes)
        self.assertEqual(v, "APPROVE")

    def test_one_dissenting_vote_escalates(self):
        votes = {"vote0": _ans("approve", 0.99), "vote1": _ans("approve", 0.97),
                 "vote2": _ans("escalate", 0.55)}
        v, _ = shim._ensemble_verdict(votes)
        self.assertEqual(v, "ESCALATE")

    def test_unanimous_deny(self):
        votes = {"vote0": _ans("deny", 0.99), "vote1": _ans("deny", 0.97),
                 "vote2": _ans("deny", 0.95)}
        v, _ = shim._ensemble_verdict(votes)
        self.assertEqual(v, "DENY")


class TestHandleChat(unittest.TestCase):
    def test_aprove_flow_returns_single_word(self):
        with patch.object(shim.dc, "ask",
                          return_value={"ok": True, "answers": {
                              "approve": _ans("approve", 0.95, 0.8)}}):
            status, body = shim.handle_chat_completions(GUARDIAN_BODY)
        self.assertEqual(status, 200)
        self.assertEqual(body["choices"][0]["message"]["content"], "APPROVE")

    def test_decider_down_is_500(self):
        with patch.object(shim.dc, "ask",
                          return_value={"ok": False, "error": "refused"}):
            status, body = shim.handle_chat_completions(GUARDIAN_BODY)
        self.assertEqual(status, 500)
        self.assertIn("error", body)

    def test_parse_failure_is_escalate_without_decider_call(self):
        with patch.object(shim.dc, "ask") as fake:
            status, body = shim.handle_chat_completions(
                {"messages": [{"role": "user", "content": "nothing"}]})
        self.assertEqual(status, 200)
        self.assertEqual(body["choices"][0]["message"]["content"], "ESCALATE")
        fake.assert_not_called()

    def test_high_impact_sends_three_votes(self):
        body = {"messages": [{"role": "user", "content":
                 "flagged as: recursive delete\n\n<command>\nrm -rf /tmp/empty-dir\n</command>\n\nx"}]}
        captured = {}

        def fake_ask(state, questions, model=None, **kw):
            captured["q"] = questions
            return {"ok": True, "answers": {n: _ans("approve", 0.99) for n in questions}}

        with patch.object(shim.dc, "ask", side_effect=fake_ask):
            status, resp = shim.handle_chat_completions(body)
        self.assertEqual(status, 200)
        self.assertEqual(len(captured["q"]), 3)
        self.assertEqual(resp["choices"][0]["message"]["content"], "APPROVE")

    def test_cache_hit_skips_decider(self):
        shim._CACHE.clear()
        with patch.object(shim.dc, "ask",
                          return_value={"ok": True, "answers": {
                              "approve": _ans("approve", 0.95, 0.8)}}) as fake:
            shim.handle_chat_completions(GUARDIAN_BODY)
            shim.handle_chat_completions(GUARDIAN_BODY)
        self.assertEqual(fake.call_count, 1)
        shim._CACHE.clear()


if __name__ == "__main__":
    unittest.main()
