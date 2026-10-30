---
name: time
description: Use when an agent must time-box work with a stopwatch.
version: 1.0.0
author: NoSleepHermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [stopwatch, time, discipline]
---

# Time (agent stopwatch)

One stdlib-only script: `scripts/stopwatch.py`. No daemon, no deps. State file: `~/.cache/agent-stopwatch.json` (name → {start, limit, label}).

## Use

```bash
python3 <skill_dir>/scripts/stopwatch.py start 3 "section 1"   # start 3-min timer
python3 <skill_dir>/scripts/stopwatch.py check                 # elapsed / remaining
python3 <workflow>...                                          # do the work
python3 <skill_dir>/scripts/stopwatch.py check                 # again; status says OVER past limit
python3 <skill_dir>/scripts/stopwatch.py stop                  # clears, prints total
```

- `start <minutes> [label] [name]` — minutes can be fractional (`0.5`). Starting an existing name restarts it.
- `check [name]` / `stop [name]` — omit name with one timer running; several timers need a name.
- Output is one line, deterministic: `label=<l> elapsed=0:01:23 limit=0:03:00 remaining=0:01:37 status=OK`
  - `status=OK` (within limit) or `status=OVER` (past it). `stop` prints `total=` instead.
- Exit codes: `0` OK/STOPPED, `1` OVER, `2` usage error. Agent rule: **check the exit code; if OVER, wrap up immediately.**
- `check` never mutates state; `stop` always clears. No `start` without a decision to obey it.

## Prompting pattern

When the user says "spend max 3min on each of the five sections": for each section run `start 3 "<section>"` on entry and `check` on every natural pause; stop or restart between sections.

Human-readable quick reference for the user: `references/README.md`.
