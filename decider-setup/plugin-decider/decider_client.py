#!/usr/bin/env python3
"""decider_client — swap-ready client for local decision models.

One entry point: ``ask(state_text, questions, model=...)``.

- Registry (``models.json`` next to this file) maps model names to endpoints:
  ``{default: <name>, models: {<name>: {base_url, api, timeout_s, ...}}}``.
  Adding a decider model later = deploy it on a port + add one registry entry;
  a new adapter class is only needed if its HTTP API differs from the ones here.
- Adapters translate (state, questions) -> HTTP request -> normalized answers.
  ``systemone``   : llama.cpp decision-head API (/v1/systemone, typed questions,
                    calibrated probabilities) — the d1-2B shape.
  ``openai_chat`` : any OpenAI-compatible chat endpoint that answers with a JSON
                    object (fallback for future general deciders).
- FAILURE CONTRACT: a transport, timeout, or parse failure returns
  ``{"ok": False, "error": ...}`` and NEVER a guessed verdict. Callers must
  treat ``ok: False`` as "decide nothing / escalate".
- Identical (model, state, questions) payloads are hash-cached in-process.

Stdlib only. Python >= 3.10.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

__all__ = ["ask", "load_registry", "list_models", "CACHE_MAX"]

CACHE_MAX = 256
_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json")

_CACHE: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_CACHE_LOCK = threading.Lock()

_VALID_QUESTION_TYPES = {"choice", "score", "noul"}


# ---------------------------------------------------------------------------
# Transport (single seam — tests mock this)
# ---------------------------------------------------------------------------

def _http_post_json(url: str, payload: dict, timeout: float) -> Any:
    """POST JSON, return decoded body. Raises on transport/HTTP failure."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def load_registry(registry_path: Optional[str] = None) -> Dict[str, Any]:
    path = registry_path or _REGISTRY_PATH
    with open(path, "r", encoding="utf-8") as fh:
        reg = json.load(fh)
    if not isinstance(reg.get("models"), dict) or not reg["models"]:
        raise ValueError(f"registry {path!r} has no models")
    default = reg.get("default")
    if default not in reg["models"]:
        raise ValueError(f"registry {path!r}: default {default!r} not in models")
    return reg


def list_models(registry_path: Optional[str] = None) -> Dict[str, Any]:
    reg = load_registry(registry_path)
    return {"default": reg["default"],
            "models": {n: {"base_url": e.get("base_url"), "api": e.get("api"),
                           "description": e.get("description", "")}
                       for n, e in reg["models"].items()}}


def _resolve(entry_name: Optional[str], registry_path: Optional[str]) -> Tuple[str, dict, float]:
    reg = load_registry(registry_path)
    name = entry_name or reg["default"]
    entry = reg["models"].get(name)
    if entry is None:
        raise KeyError(f"unknown model {name!r} (known: {', '.join(sorted(reg['models']))})")
    if entry.get("api") not in ADAPTERS:
        raise KeyError(
            f"model {name!r}: unknown api adapter {entry.get('api')!r} "
            f"(known: {', '.join(sorted(ADAPTERS))})")
    return name, entry, float(entry.get("timeout_s", 60))


# ---------------------------------------------------------------------------
# Question normalization / validation
# ---------------------------------------------------------------------------

def _normalize_questions(questions: Any) -> Dict[str, dict]:
    """Accept dict {name: spec} or list [{name, ...spec}] -> validated dict."""
    if isinstance(questions, list):
        qd: Dict[str, dict] = {}
        for q in questions:
            if not isinstance(q, dict) or not q.get("name"):
                raise ValueError("list-form questions need a 'name' field each")
            name = q["name"]
            if name in qd:
                raise ValueError(f"duplicate question name {name!r}")
            qd[name] = {k: v for k, v in q.items() if k != "name"}
        questions = qd
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions must be a non-empty dict or list")
    for name, spec in questions.items():
        if not isinstance(spec, dict):
            raise ValueError(f"question {name!r}: spec must be an object")
        if spec.get("type") not in _VALID_QUESTION_TYPES:
            raise ValueError(
                f"question {name!r}: type must be one of {sorted(_VALID_QUESTION_TYPES)}")
    return questions


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

def _ask_systemone(entry: dict, state_text: str, questions: dict,
                   timeout: float) -> Dict[str, Any]:
    url = entry["base_url"].rstrip("/") + "/v1/systemone"
    body = _http_post_json(url, {"state": {"text": state_text}, "questions": questions},
                           timeout)
    if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
        raise ValueError("systemone response missing 'answers' object")
    return {"answers": body["answers"], "usage": body.get("usage"),
            "raw_model": body.get("model")}


def _ask_openai_chat(entry: dict, state_text: str, questions: dict,
                     timeout: float) -> Dict[str, Any]:
    url = entry["base_url"].rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": entry.get("upstream_model") or "decider",
        "temperature": 0,
        "messages": [
            {"role": "system",
             "content": ("You are a decision endpoint. Reply with ONLY a JSON object "
                         'of the form {"answers": {<question name>: <answer>, ...}} — '
                         "no prose, no markdown fences.")},
            {"role": "user", "content": json.dumps(
                {"state": state_text, "questions": questions})},
        ],
    }
    body = _http_post_json(url, payload, timeout)
    content = body["choices"][0]["message"]["content"]  # KeyError => parse failure
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("openai_chat content is not a JSON object")
    answers = parsed.get("answers") if isinstance(parsed.get("answers"), dict) else parsed
    if not isinstance(answers, dict) or not answers:
        raise ValueError("openai_chat content carries no answers")
    return {"answers": answers, "usage": body.get("usage"),
            "raw_model": body.get("model")}


ADAPTERS = {"systemone": _ask_systemone, "openai_chat": _ask_openai_chat}


# ---------------------------------------------------------------------------
# Cache + public entry point
# ---------------------------------------------------------------------------

def _cache_key(model: str, state_text: str, questions: dict) -> str:
    blob = json.dumps({"m": model, "s": state_text, "q": questions},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def ask(state_text: str, questions: Any, model: Optional[str] = None,
        registry_path: Optional[str] = None, timeout: Optional[float] = None,
        use_cache: bool = True) -> Dict[str, Any]:
    """Ask a decider model. Returns on success::

        {"ok": True, "model": <name>, "answers": {...}, "usage": {...},
         "latency_s": <float>, "cached": <bool>}

    and on ANY failure::

        {"ok": False, "error": "<reason>", "model": <name or None>}

    ``answers`` maps each question name to its typed answer (for systemone:
    {type, choice|value, probabilities{...}, confidence}). Never raises for
    remote problems — callers decide how to escalate.
    """
    t0 = time.monotonic()
    try:
        name, entry, default_timeout = _resolve(model, registry_path)
        questions = _normalize_questions(questions)
    except Exception as exc:  # config/validation problems: fail before any I/O
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "model": None}

    key = _cache_key(name, state_text, questions)
    if use_cache:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
            if hit is not None:
                _CACHE.move_to_end(key)
                return {**hit, "cached": True, "latency_s": round(time.monotonic() - t0, 4)}

    adapter = ADAPTERS[entry["api"]]
    try:
        result = adapter(entry, state_text, questions, timeout or default_timeout)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "model": name}

    out = {"ok": True, "model": name, "cached": False,
           "latency_s": round(time.monotonic() - t0, 4), **result}
    if use_cache:
        with _CACHE_LOCK:
            _CACHE[key] = out
            _CACHE.move_to_end(key)
            while len(_CACHE) > CACHE_MAX:
                _CACHE.popitem(last=False)
    return out
