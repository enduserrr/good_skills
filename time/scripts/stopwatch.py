#!/usr/bin/env python3
"""agent-stopwatch: deterministic timers for agent self-discipline.

Usage:
  stopwatch.py start <minutes> [label] [name]
  stopwatch.py check [name]
  stopwatch.py stop  [name]

Exit codes: 0 = OK/stopped, 1 = OVER limit, 2 = usage error.
State: ~/.cache/agent-stopwatch.json
"""
import json, sys, time, os

STATE = os.path.expanduser("~/.cache/agent-stopwatch.json")


def _fmt(sec: float) -> str:
    s = int(round(sec))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _load() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(d, f)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    cmd = argv[1]
    timers = _load()

    if cmd == "start":
        if len(argv) < 3:
            print("usage: start <minutes> [label] [name]", file=sys.stderr)
            return 2
        try:
            minutes = float(argv[2])
            assert minutes > 0
        except (ValueError, AssertionError):
            print("error: minutes must be positive", file=sys.stderr)
            return 2
        label = argv[3] if len(argv) > 3 else ""
        name = argv[4] if len(argv) > 4 else "default"
        now = time.time()
        timers[name] = {"start": now, "limit": minutes * 60.0, "label": label or name}
        _save(timers)
        t = timers[name]
        print(f"name={name} label={t['label']} limit={_fmt(t['limit'])} started status=OK")
        return 0

    if cmd in ("check", "stop"):
        if len(argv) > 2:
            name = argv[2]
        else:
            name = "default" if "default" in timers else (next(iter(timers), None))
        if name is None or name not in timers:
            print("error: no running timer", file=sys.stderr)
            return 2
        t = timers[name]
        elapsed = time.time() - t["start"]
        over = elapsed > t["limit"]
        if cmd == "stop":
            del timers[name]
            _save(timers)
            print(f"label={t['label']} total={_fmt(elapsed)} limit={_fmt(t['limit'])} status=STOPPED")
            return 0
        status = "OVER" if over else "OK"
        remaining = max(0.0, t["limit"] - elapsed)
        print(
            f"label={t['label']} elapsed={_fmt(elapsed)} limit={_fmt(t['limit'])} "
            f"remaining={_fmt(remaining)} status={status}"
        )
        return 1 if over else 0

    print(f"error: unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
