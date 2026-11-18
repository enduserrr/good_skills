"""decider plugin — exposes the swap-ready `decide` tool.

Tool contract (mirror of scripts/decide + decider_client.ask):
  decide(state_context, questions[], model?, use_cache?) -> JSON string
    ok:true  -> {model, answers{...}, usage, latency_s, cached}
    ok:false -> {error}                      # NEVER a guessed verdict

The plugin registers ONLY this ask-a-question tool. Approval veto/guardian
machinery is deliberately NOT here (plan Task C, separate gate); this tool can
never approve or deny anything by itself — it answers questions.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.parse
from typing import Any, Dict

from . import decider_client

_CHECK_TTL_S = 60.0
_last_check = 0.0
_last_ok = False

DESCRIPTION = (
    "Ask a registered local decider model (default d1-2b) batched "
    "typed questions in ONE request; returns calibrated probabilities + "
    "confidence per question. Use for safety screens, triage, routing, "
    "spawn/review gates. Not for chat, vision, or multi-step reasoning. "
    "ok:false = decider unreachable/invalid — decide nothing, escalate."
)

_SCHEMA = {
    "name": "decide",
    "description": DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {
            "state_context": {
                "type": "string",
                "description": "The situation text the decider conditions on "
                               "(command under consideration, URLs found, task "
                               "summary...). Keep it <=~250 tokens; facts only.",
            },
            "questions": {
                "type": "array",
                "description": "1–8 questions, batched (one POST amortizes the "
                               "~10 s pass). Each: {name, type: choice|score|noul, "
                               "instructions, criteria: {option: description}}.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string",
                                 "enum": ["choice", "score", "noul"]},
                        "instructions": {"type": "string"},
                        "criteria": {"type": "object"},
                    },
                    "required": ["name", "type", "instructions"],
                },
            },
            "model": {"type": "string",
                      "description": "Registry name (scripts/decide --list-models); "
                                     "omit for the registry default."},
            "use_cache": {"type": "boolean", "default": True},
        },
        "required": ["state_context", "questions"],
    },
}


def _default_endpoint_reachable() -> bool:
    """Cheap TCP probe of the registry default; cached 60 s. Fail-closed."""
    global _last_check, _last_ok
    now = time.monotonic()
    if now - _last_check < _CHECK_TTL_S:
        return _last_ok
    try:
        entry = decider_client.load_registry()["models"][
            decider_client.load_registry()["default"]]
        host = entry["base_url"].split("//", 1)[-1].rstrip("/")
        host, port = host.split(":")[0], int(host.split(":")[1])
        with socket.create_connection((host, port), timeout=1.0):
            pass
        _last_ok = True
    except Exception:
        _last_ok = False
    _last_check = now
    return _last_ok


def decide_tool(args: Dict[str, Any], **_: Any) -> str:
    out = decider_client.ask(
        state_text=str(args.get("state_context") or ""),
        questions=args.get("questions") or [],
        model=args.get("model"),
        use_cache=bool(args.get("use_cache", True)),
    )
    return json.dumps(out)


def register(ctx) -> None:
    """Plugin entry point (plugins/plugin_loader.py contract)."""
    ctx.register_tool(
        name="decide", toolset="decider", schema=_SCHEMA, handler=decide_tool,
        description=DESCRIPTION, emoji="⚖️", check_fn=_default_endpoint_reachable,
    )
