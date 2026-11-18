#!/usr/bin/env python3
"""Regression suite for the decider probe-form harness.

Runs fixtures (references/fixtures/*.form.md) through consult.py --tag REGR and
compares verdicts/zones against references/expected.json. Live decider POSTs:
full run ~6 min; pass stem substrings to run subsets (e.g. `r0 p0`).

Exit 0 = all hard expectations met (ANY/known-soft entries recorded only).
"""
import json
import pathlib
import re
import subprocess
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CONSULT = SCRIPT_DIR / "consult.py"


def _locate(name, need_dir=False):
    """Find references/<name> whether the script sits in scripts/ (skill
    layout) or flat beside the references dir (dev layout)."""
    for base in (SCRIPT_DIR.parent, SCRIPT_DIR):
        p = base / "references" / name
        if p.is_dir() if need_dir else p.is_file():
            return p
    sys.exit("references/%s not found (fail-closed)" % name)


FIXTURES = _locate("fixtures", need_dir=True)
EXPECTED = _locate("expected.json")

VERDICT_RE = re.compile(
    r"FORM REFUSED|(?:^audit: \S+ \| (?:\S+ )?(RUN|BLOCK_AND_FIX|BLOCK_ENTIRELY|ASK_USER))",
    re.M)


def run_one(stem):
    form = FIXTURES / (stem + ".form.md")
    r = subprocess.run([sys.executable, str(CONSULT), str(form), "--tag", "REGR"],
                       capture_output=True, text=True, timeout=180)
    out = r.stdout + r.stderr
    if "FORM REFUSED" in out:
        return "REFUSED", out
    m = VERDICT_RE.search(out)
    return (m.group(1) if m and m.group(1) else "?"), out


def main():
    args = [a for a in sys.argv[1:]]
    expected = json.loads(EXPECTED.read_text())
    stems = [s for s in sorted(expected)
             if not args or any(a in s for a in args)]
    hard_fail, rows, notes = 0, [], []
    for stem in stems:
        e = expected[stem]
        verdict, out = run_one(stem)
        zone_m = re.search(r"path classification: (.+)", out)
        zone = zone_m.group(1) if zone_m else ""
        ok = True
        why = ""
        if e["expect"] == "REFUSED":
            ok = verdict == "REFUSED" and e["err"] in out
            why = "" if ok else "expected refuse w/ '%s'" % e["err"]
        elif e["expect"] == "ANY":
            ok = verdict in ("RUN", "BLOCK_AND_FIX", "BLOCK_ENTIRELY", "ASK_USER")
            why = "record-only"
            notes.append("%s -> %s%s" % (stem, verdict,
                         ("; " + e["note"]) if e.get("note") else ""))
        elif e["expect"] == "RUN":
            ok = verdict == "RUN"
            why = "" if ok else "expected RUN, got %s" % verdict
        elif e["expect"] == "BLOCK":
            ok = verdict in ("BLOCK_AND_FIX", "BLOCK_ENTIRELY")
            why = "" if ok else "expected BLOCK_*, got %s" % verdict
        if e.get("zone") and ok:
            ok = e["zone"] in zone
            why = why or ("zone mismatch: wanted '%s', got '%s'"
                          % (e["zone"], zone[:60]))
        if not ok:
            hard_fail += 1
        rows.append((stem, verdict, e["expect"], "PASS" if ok else "FAIL: " + why))

    w = max(len(r[0]) for r in rows)
    for stem, verdict, exp, res in rows:
        print("%-*s got=%-14s want=%-8s %s" % (w, stem, verdict, exp, res))
    print("\n%d/%d hard expectations met" % (len(rows) - hard_fail, len(rows)))
    for n in notes:
        print("note:", n)
    sys.exit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()
