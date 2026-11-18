#!/usr/bin/env python3
"""delegation_gate — the user-owned opt-in gate for delegated approval sessions.

The gate file is the single source of truth for whether launching sessions in
the ``decider`` profile (tool approvals answered by a decider model) is
currently permitted. Only the USER should flip it (scripts/decide-admin);
everything that launches delegated sessions must refuse unless the gate says
``allowed``.

Honest limit: user and agents share one OS account, so this gate is an
audit-friendly switch, not a cryptographic boundary. The structural guarantees
live in the wrapper: it only ever LAUNCHES new sessions and never mutates any
session's config.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
DEFAULT_GATE_PATH = PLUGIN_DIR / "data" / "approval-delegation.json"
ALLOWED, OFF = "allowed", "off"


def gate_path() -> Path:
    return Path(os.environ.get("DECIDER_GATE", DEFAULT_GATE_PATH))


def read_gate(path: Path | None = None) -> dict:
    """Missing or corrupt gate => off (fail-closed)."""
    p = path or gate_path()
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("state") not in (ALLOWED, OFF):
            return {"state": OFF, "note": "corrupt gate value treated as off"}
        return doc
    except (OSError, json.JSONDecodeError):
        return {"state": OFF, "note": "unset"}


def write_gate(state: str, note: str = "", path: Path | None = None) -> dict:
    p = path or gate_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"state": state, "note": note,
           "updated": datetime.datetime.now().isoformat(timespec="seconds")}
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def is_allowed(path: Path | None = None) -> bool:
    return read_gate(path).get("state") == ALLOWED
