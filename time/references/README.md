# agent stopwatch — quick reference

Three commands, one line of output, no daemon.

```bash
S=<skills-dir>/time/scripts/stopwatch.py   # adjust to where the skill lives
python3 $S start 3 "section 1"   # 3-minute timer
python3 $S check                 # label=... elapsed=0:01:23 limit=0:03:00 remaining=0:01:37 status=OK
python3 $S stop                  # clears, prints total
```

- `status=OK` within the limit, `status=OVER` past it; exit code `1` when OVER, `0` otherwise, `2` on usage error.
- Minutes may be fractional (`0.5`). Starting an existing name restarts it.
- With several timers, pass a name: `start 3 "label" name2`, `check name2`.
- State lives in `~/.cache/agent-stopwatch.json`; deleting that file resets everything.
