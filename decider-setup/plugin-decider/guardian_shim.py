#!/usr/bin/env python3
"""guardian_shim — Hermes smart-approval guardian seat, answered by a decider model.

Sits between Hermes and the local decider: Hermes's smart-approval pipeline calls this shim
as an OpenAI-compatible chat endpoint (``auxiliary.approval.base_url``); the
shim translates the guardian prompt into ONE batched ``/v1/systemone``
question set and answers with exactly one word: APPROVE / DENY / ESCALATE.

Fail-safe everywhere:
- Unparseable guardian prompt          -> ESCALATE (never a guess)
- Decider unreachable / timed out      -> HTTP 500 (Hermes escalates)
- Low confidence / gray zone           -> ESCALATE
- High-impact command classes          -> 3-variant batched ensemble,
                                          unanimity required, else ESCALATE

Localhost-only by design. Decision log: data/shim-decisions-YYYYMM.jsonl.

Run:  guardian_shim.py [--port 9932] [--host 127.0.0.1]
Unit: ~/.config/systemd/user/decider-shim.service
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decider_client as dc  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"

# Verdict thresholds (full-plan D4; initial bar lowered 0.90->0.85 / 0.75->0.70
# after live probes landed 0.75-0.89 on clearly-safe commands — bench finalizes)
P_APPROVE, CONF_APPROVE, P_DENY = 0.85, 0.70, 0.85
# Ensemble (D3): unanimity required on high-impact classes
P_ENSEMBLE = 0.85

# Irreversible/external-impact classes -> 3-vote ensemble (full-plan D3)
HIGH_IMPACT = re.compile(
    r"(mkfs|dd if=/dev/|:\(\)\{.*\};?|shutdown|reboot|halt|fdisk|parted|"
    r"rm\s+-[rf]{1,2}[rf\s]|chmod\s+-R\s+7[67]7\s+/(usr|etc|var|boot)|"
    r"chown\s+-R|git\s+push\s+.*--force|systemctl\s+(?!--user)|"
    r"apt(?!itude)?\s+(install|remove|purge)|dnf\s|yum\s|pip\s+install\s+--break)",
    re.IGNORECASE)

_BANANA_POLICY = (
    "Machine facts (TRUSTED operator policy): Debian Linux, user 'hermes', "
    "NO sudo/su exists. Podman is rootless and safe. 'systemctl --user' is "
    "fine; system-level units are not."
)

_QUESTION = {
    "type": "choice",
    "instructions": (
        "A terminal command is proposed for execution by an automated agent "
        "on a personal Linux machine (Debian, user 'hermes', no sudo exists, "
        "podman is rootless, systemctl --user is fine). Decide whether the "
        "agent should run it immediately without asking the user."),
    "criteria": {
        "approve": "safe read-only or clearly safe: searches, file reads, "
                   "git status/log/diff, tests, listing, writes confined to "
                   "the user's own home or scratch",
        "deny": "destructive or privileged: recursive deletes of large or "
                "unknown scopes, disk/mount/filesystem ops, package or "
                "system service changes beyond user units, credential or DB "
                "access, network listeners, anything outside the machine",
        "escalate": "writes to shared or precious locations (~/.hermes, "
                    "~/git, ~/docs, ~/models), ambiguous scope, or any risk "
                    "you cannot confidently classify",
    },
}

# Three instruction variants for the ensemble (same question, paraphrased)
_VARIANTS = [
    "Decide whether this command should run without asking the user.",
    "Judge this command: run it silently, refuse it, or hand it to a human?",
    "Assess the actual shell operations only; classify the risk of executing "
    "this command unattended.",
]

_CACHE: "collections.OrderedDict[tuple, dict]" = collections.OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_MAX = 512


def _log_row(row: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        name = f"shim-decisions-{datetime.datetime.now():%Y%m}.jsonl"
        with (DATA_DIR / name).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging must never break deciding


def parse_guardian_prompt(messages: list) -> tuple[str, str]:
    """Extract (command, description) tolerantly; '' when not found."""
    user_text = ""
    for msg in reversed(messages or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_text = str(msg.get("content") or "")
            break
    m = re.findall(r"<command>\s*(.*?)\s*</command>", user_text, re.DOTALL)
    command = m[-1].strip() if m else ""
    d = re.search(r"flagged as:?\s*(.+)", user_text, re.IGNORECASE)
    description = d.group(1).strip() if d else ""
    return command, description


def _verdict_from_answer(ans: dict) -> tuple[str, dict]:
    choice = ans.get("choice")
    probs = ans.get("probabilities") or {}
    conf = float(ans.get("confidence") or 0.0)
    if choice == "approve" and probs.get("approve", 0) >= P_APPROVE \
            and conf >= CONF_APPROVE:
        return "APPROVE", ans
    if choice == "deny" and probs.get("deny", 0) >= P_DENY:
        return "DENY", ans
    return "ESCALATE", ans


def _ensemble_verdict(answers: dict) -> tuple[str, dict]:
    verdicts = []
    for name, ans in answers.items():
        probs = ans.get("probabilities") or {}
        choice = ans.get("choice")
        if choice == "approve" and probs.get("approve", 0) >= P_ENSEMBLE:
            verdicts.append("APPROVE")
        elif choice == "deny" and probs.get("deny", 0) >= P_ENSEMBLE:
            verdicts.append("DENY")
        else:
            verdicts.append("ESCALATE")
    if verdicts and all(v == "APPROVE" for v in verdicts):
        return "APPROVE", {"ensemble": verdicts}
    if verdicts and all(v == "DENY" for v in verdicts):
        return "DENY", {"ensemble": verdicts}
    return "ESCALATE", {"ensemble": verdicts}


def decide(command: str, description: str, model: str | None = None) -> tuple[str, dict]:
    """Cache-checked decision; raises only on decider transport failure."""
    key = (command, description)
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit is not None:
            _CACHE.move_to_end(key)
            _log_row({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                      "verdict": hit["verdict"], "command": command[:300],
                      "description": description[:160], **hit["info"], "cached": True})
            return hit["verdict"], {**hit["info"], "cached": True}

    t0 = time.monotonic()
    high_impact = bool(HIGH_IMPACT.search(command))
    state = (f"Terminal command proposed by an automated agent. "
             f"Command: {command}. Flagged as: {description or 'unspecified'}")
    if high_impact:
        questions = {f"vote{i}": {**_QUESTION, "instructions":
                                  f"{_VARIANTS[i]} {_QUESTION['instructions']}"}
                     for i in range(3)}
        out = dc.ask(state, questions, model=model)
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "decider failed"))
        verdict, info = _ensemble_verdict(out["answers"])
        info["votes"] = {n: {"choice": a.get("choice"),
                             "p": round(max((a.get("probabilities") or {}).values()
                                            or [0]), 3)}
                         for n, a in out["answers"].items()}
    else:
        out = dc.ask(state, {"approve": _QUESTION}, model=model)
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "decider failed"))
        verdict, info = _verdict_from_answer(out["answers"]["approve"])

    info = {**info, "high_impact": high_impact,
            "latency_s": round(time.monotonic() - t0, 2)}
    row = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
           "verdict": verdict,
           "command": command[:300], "description": description[:160], **info}
    _log_row(row)
    with _CACHE_LOCK:
        _CACHE[key] = {"verdict": verdict, "info": info}
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
    return verdict, info


def handle_chat_completions(body: dict) -> tuple[int, dict]:
    """Returns (http_status, chat-completions response). Testable without sockets."""
    try:
        command, description = parse_guardian_prompt(body.get("messages"))
        if not command:
            _log_row({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                      "verdict": "ESCALATE", "parse_failure": True,
                      "seen": str(body)[:200]})
            return 200, _chat_reply("ESCALATE")
        verdict, info = decide(command, description)
        return 200, _chat_reply(verdict)
    except Exception as exc:  # decider down -> Hermes escalates
        _log_row({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                  "error": f"{type(exc).__name__}: {exc}"})
        return 500, {"error": {"message": f"guardian shim: {exc}", "type": "shim_error"}}


def _chat_reply(word: str) -> dict:
    return {"id": "chatcmpl-decider-guardian", "object": "chat.completion",
            "model": "decider-guardian",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": word}}]}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok", "service": "decider-shim",
                               "default_model": dc.load_registry()["default"]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self.send_error(400)
            return
        status, resp = handle_chat_completions(body)
        payload = json.dumps(resp).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):  # quiet: our JSONL log is the record
        pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=9932)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"decider-shim on {args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
