"""Gate + wrapper refusal tests — isolated via env overrides, no live calls."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
ADMIN = str(PLUGIN_DIR / "scripts" / "decide-admin")
SESSION = str(PLUGIN_DIR / "scripts" / "decide-session")


def _iso_env(tmp, **over):
    env = dict(os.environ)
    env["DECIDER_GATE"] = str(Path(tmp) / "gate.json")
    env.update({k: str(v) for k, v in over.items()})
    return env


def _run(script, args, env):
    return subprocess.run([sys.executable, script, *args], env=env,
                          capture_output=True, text=True, timeout=30)


class TestGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = _iso_env(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_unset_gate_is_off_and_status_reports_it(self):
        r = _run(ADMIN, ["status"], self.env)
        self.assertEqual(r.returncode, 0)
        self.assertIn('"state": "off"', r.stdout)

    def test_allow_then_status_allowed(self):
        self.assertEqual(_run(ADMIN, ["allow"], self.env).returncode, 0)
        r = _run(ADMIN, ["status"], self.env)
        self.assertIn('"state": "allowed"', r.stdout)

    def test_pause_is_kill_switch_to_off(self):
        _run(ADMIN, ["allow"], self.env)
        r = _run(ADMIN, ["pause"], self.env)
        self.assertIn('"state": "off"', r.stdout)
        self.assertIn("PAUSED", r.stdout)

    def test_corrupt_gate_reads_as_off(self):
        Path(self.env["DECIDER_GATE"]).write_text("{busted")
        r = _run(ADMIN, ["status"], self.env)
        self.assertIn('"state": "off"', r.stdout)


class TestDecideSessionRefusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.qf = Path(self.tmp.name) / "query.md"
        self.qf.write_text("# probe task\n")
        self.env = _iso_env(self.tmp.name,
                            DECIDER_PROFILE_DIR=Path(self.tmp.name) / "profile")

    def tearDown(self):
        self.tmp.cleanup()

    def test_gate_off_refuses_before_anything(self):
        r = _run(SESSION, ["--query-file", str(self.qf), "--dry-run"], self.env)
        self.assertEqual(r.returncode, 3)
        self.assertIn("REFUSED", r.stderr)
        self.assertIn("decide-admin allow", r.stderr)

    def test_allowed_but_no_profile_refuses_launch(self):
        subprocess.run([sys.executable, ADMIN, "allow"], env=self.env,
                       capture_output=True)
        r = _run(SESSION, ["--query-file", str(self.qf), "--dry-run"], self.env)
        self.assertEqual(r.returncode, 4)
        self.assertIn("not built yet", r.stderr)

    def test_allowed_with_profile_dry_run_prints_command(self):
        subprocess.run([sys.executable, ADMIN, "allow"], env=self.env,
                       capture_output=True)
        (Path(self.tmp.name) / "profile").mkdir()
        r = _run(SESSION, ["--query-file", str(self.qf), "--dry-run"], self.env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("hermes -p decider chat", r.stdout)
        self.assertIn("--query-file", r.stdout)
        self.assertIn("tmux new-session -d", r.stdout)

    def test_missing_query_file_is_usage_error(self):
        subprocess.run([sys.executable, ADMIN, "allow"], env=self.env,
                       capture_output=True)
        r = _run(SESSION, ["--query-file", "/nonexistent/x.md"], self.env)
        self.assertEqual(r.returncode, 2)


class ScriptsExecutable(unittest.TestCase):
    def test_scripts_are_executable(self):
        for s in ("decide", "decide-admin", "decide-session"):
            mode = os.stat(PLUGIN_DIR / "scripts" / s).st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"{s} not executable")


if __name__ == "__main__":
    unittest.main()
