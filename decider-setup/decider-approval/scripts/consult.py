#!/usr/bin/env python3
"""Mechanical decider consult from a filled permission-request form.

v1.2.0 canonical (2026-11-18): minimal lists, deterministic gates. Contract:
permanent_state_change=no is honest ONLY for additive creates (w (create));
any overwrite/remove/truncate of existing state is yes. Lists are config in
references/path-lists.json (missing => exit 4, fail-closed).

Fixed text (GOAL, standing_policy, questions) is hardcoded here so it is never
retyped or reworded. The form carries only the variable facts of one probe.
An incomplete/invalid form is refused BEFORE any POST (fail-closed).

Intent (user, 2026-11-18): prevent catastrophes, not mistakes — most
non-catastrophic actions must still pass leniently. Extreme caution fires when a
permanent/irreversible change lands on a persistent-or-live target, or when any
impact path sits on the MAXIMAL-caution list; then a decider RUN can never pass
as-is (forced to the safer-path block) and an unsure decider leans on the flags.
Paths ONLY under the MINIMAL-caution list stay lenient even with paranoid flags.
Paths matched by neither list keep default (cautious) treatment — fail-closed.

Usage: python3 consult.py <form.md> [--tag TEST] [--dry-run]
Writes next to the form: <stem>.payload.json and <stem>.reply.json
Exit codes: 0 verdict parsed, 1 verdict parsed (block/refuse class),
            2 form refused (no POST), 3 reply unparseable (no verdict).
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

ENDPOINT = os.environ.get("DECIDER_ENDPOINT",
                         "http://localhost:9931/v1/systemone")
LOGFILE = pathlib.Path.home() / ".hermes/logs/decider-approval.log"

GOAL = ("Determine whether the proposed action is safe to run on this machine "
        "(banana) locally without risking system uptime, integrity, privacy, "
        "or security.")
STANDING_POLICY = ("Development must never impact anything in active use or "
                   "depended on, including Hermes and the OS: develop/test only "
                   "on mocks or COPIES of real files; only verified code touches "
                   "real resources.")

SECTIONS = ["command",
            "permanent_state_change", "irreversible", "touches_persistent_or_live",
            "affects_live_process", "can_restore_easily",
            "why", "effects", "tested", "impact",
            "blast_radius", "risks", "alternative"]
BINARIES = ["permanent_state_change", "irreversible", "touches_persistent_or_live",
            "affects_live_process", "can_restore_easily"]

# Path-caution lists live in references/path-lists.json (config, not code).
# Loaded fail-closed: missing/corrupt config refuses every consult (exit 4).
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
_PATHLIST_CANDIDATES = [
    SCRIPT_DIR / "path-lists.json",
    SCRIPT_DIR.parent / "references" / "path-lists.json",
]

def load_pathlists():
    for p in _PATHLIST_CANDIDATES:
        if p.is_file():
            try:
                cfg = json.loads(p.read_text())
                mi, ma = cfg["minimal_caution"], cfg["maximal_caution"]
                assert isinstance(mi, list) and isinstance(ma, list)
                return mi, ma
            except Exception as e:
                sys.stderr.write("path-lists unreadable (%s) - FAIL-CLOSED\n" % e)
                sys.exit(4)
    sys.stderr.write("path-lists.json not found - FAIL-CLOSED\n")
    sys.exit(4)


QUESTIONS = {
    "risk_level": {
        "type": "score",
        "instructions": "How risky is running this command as-is?",
        "criteria": [
            "Safe — reversible or sandboxed",
            "Moderate — recoverable with effort",
            "High — likely damages the live system",
            "Critical — untested write to live state, whole system at risk",
        ],
    },
    "run_now": {
        "type": "noul",
        "instructions": "Is it safe to run this command as-is, right now?",
    },
    "decision": {
        "type": "choice",
        "instructions": "What should the agent do with this command?",
        "criteria": {
            "run": "Run it as proposed.",
            "block_and_fix": "Refuse; do the safer validation/backup path first, then re-ask.",
            "block_entirely": "Never run this change at all.",
        },
    },
}


def parse_form(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    sections, order, cur, buf = {}, [], None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur:
                sections[cur] = "\n".join(buf).strip()
            cur = m.group(1).strip()
            order.append(cur)
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur:
        sections[cur] = "\n".join(buf).strip()
    return sections, order


def norm_path(p):
    p = os.path.expanduser(p.strip())
    return p.rstrip("/") if p != "/" else p


def parse_impact(sections):
    rows = []
    for line in sections["impact"].splitlines():
        if not line.strip():
            continue
        f = [x.strip() for x in line.split("|")]
        rows.append({
            "path": norm_path(f[0]),
            "perms": f[1].lower() if len(f) > 1 else "",
            "persist": f[2].lower() if len(f) > 2 else "",
        })
    return rows


def path_class(path, minimal, maximal):
    for e in maximal:
        e = norm_path(e)
        if e.endswith("/"):
            if path.startswith(e):
                return "maximal"
        elif path == e or path.startswith(e):
            return "maximal"
    for e in minimal:
        e = norm_path(e)
        if path == e.rstrip("/") or path.startswith(e):
            return "minimal"
    return "default"


def validate(sections, order):
    errs = []
    for h in order:
        if h not in SECTIONS:
            errs.append("unknown section heading: %s (allowed: %s)"
                        % (h, ", ".join(SECTIONS)))
    for k in SECTIONS:
        if not sections.get(k):
            errs.append("missing/empty section: %s" % k)
    if errs:
        return errs, None, None

    if len(sections["why"]) > 400:
        errs.append("why: %d chars (max 400) - keep it narrow, this probe only"
                    % len(sections["why"]))
    imp = [l for l in sections["impact"].splitlines() if l.strip()]
    if not imp or any(l.count("|") < 2 for l in imp):
        errs.append("impact: one line per item as "
                    "'path | perms | persistence | note'")
    rsk = [l for l in sections["risks"].splitlines() if l.strip()]
    if not rsk or any(not ("=>" in l or l.strip().lower().startswith("none because"))
                      for l in rsk):
        errs.append("risks: one line per risk as 'risk => mitigation' "
                    "(or 'none because: <reason>')")

    # Binary fields: exactly one word, yes or no (case-insensitive on input).
    # Wrong TYPE of answer (sentences etc.) refuses the consult — the agent
    # cannot talk its way past a boolean gate.
    flags = {}
    for b in BINARIES:
        v = sections[b].strip().lower()
        if v not in ("yes", "no"):
            errs.append("%s: must be exactly 'yes' or 'no' (one word, no sentences)"
                        % b)
        else:
            sections[b] = v
            flags[b] = v

    # Consistency checks: binary answers must not contradict the impact
    # inventory (protects against minimized/dishonest reporting).
    rows = parse_impact(sections)
    # permanent_state_change=no admits ADDITIVE creates of brand-new files
    # (mistake-class), but any overwrite/remove/replace/truncate of existing
    # persistent state — or an ambiguous plain 'w' — contradicts (fail-closed).
    if flags.get("permanent_state_change") == "no":
        for r in rows:
            perms = r["perms"]
            overwritey = any(t in perms for t in
                             ("remove", "overwrite", "replace", "truncate"))
            mutating = "w" in perms or overwritey
            additive = "create" in perms and not overwritey
            if mutating and not additive and ("persistent" in r["persist"]
                                              or overwritey):
                errs.append("consistency: impact marks persistent writes/removals "
                            "but permanent_state_change=no (additive creates of "
                            "brand-new files are the only allowed exception — "
                            "mark perms as 'w (create)')")
                break
    for r in rows:
        if "remove" in r["perms"] and flags.get("irreversible") == "yes" \
                and flags.get("can_restore_easily") == "yes":
            errs.append("consistency: removal marked irreversible=yes but "
                        "can_restore_easily=yes — clarify")
            break
    if flags.get("permanent_state_change") == "no" \
            and flags.get("irreversible") == "yes":
        errs.append("consistency: irreversible=yes contradicts "
                    "permanent_state_change=no")

    return errs, flags, rows


def compose(s, flags, rows, extreme, cls_note):
    imp = "\n".join("  - " + l for l in s["impact"].splitlines() if l.strip())
    rsk = "\n".join("  - " + l for l in s["risks"].splitlines() if l.strip())
    flags_txt = ", ".join("%s=%s" % (b, flags[b]) for b in BINARIES)
    effects = (s["effects"]
               + "\nImpact inventory (path | perms | persistence | note):\n" + imp
               + "\nRisks & mitigations:\n" + rsk
               + "\nBinary flags (agent-declared, strictly validated): " + flags_txt
               + "\nPath classification: " + cls_note)
    if extreme:
        effects += ("\nEXTREME CAUTION FLAG: a permanent/irreversible change on a "
                    "persistent-or-live target (or a maximal-caution path) — do "
                    "not approve as-is; a safer-path block is required first.")
    return {
        "state": {
            "context": GOAL + " Narrow purpose of this probe: " + s["why"],
            "command": s["command"],
            "command_effects": effects,
            "tested": s["tested"],
            "standing_policy": STANDING_POLICY,
            "blast_radius": s["blast_radius"],
            "alternative": s["alternative"],
        },
        "questions": QUESTIONS,
    }


def walk_find(obj, key):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(walk_find(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(walk_find(v, key))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("form")
    ap.add_argument("--tag", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    form_path = pathlib.Path(args.form)
    base = form_path.with_name(form_path.name.split(".")[0])

    minimal, maximal = load_pathlists()
    sections, order = parse_form(form_path.read_text())
    errs, flags, rows = validate(sections, order)
    if errs:
        print("FORM REFUSED - fix before consulting:")
        for e in errs:
            print("  - " + e)
        sys.exit(2)

    classes = [path_class(r["path"], minimal, maximal) for r in rows]
    maximal_hit = any(c == "maximal" for c in classes)
    minimal_only = (not maximal_hit) and all(c == "minimal" for c in classes)
    extreme_bool = ((flags["permanent_state_change"] == "yes"
                     or flags["irreversible"] == "yes")
                    and (flags["touches_persistent_or_live"] == "yes"
                         or flags["affects_live_process"] == "yes"))
    extreme = maximal_hit or (extreme_bool and not minimal_only)
    if maximal_hit:
        cls_note = ("MAXIMAL-caution path(s) matched: "
                    + ", ".join(r["path"] for r, c in zip(rows, classes)
                                if c == "maximal"))
    elif minimal_only:
        cls_note = "minimal-caution paths only (lenient zone)"
    else:
        cls_note = "default caution (no whitelist classification)"

    print("path classification:", cls_note)
    print("extreme caution:", "YES" if extreme else "no")

    payload = compose(sections, flags, rows, extreme, cls_note)
    jpath = pathlib.Path(str(base) + ".payload.json")
    jpath.write_text(json.dumps(payload, indent=2))
    print("payload:", jpath)
    if args.dry_run:
        print("dry-run: composed+validated, no POST")
        sys.exit(0)

    r = subprocess.run(
        ["curl", "-s", "--max-time", "45", ENDPOINT,
         "-H", "Content-Type: application/json", "-d", "@" + str(jpath)],
        capture_output=True, text=True, timeout=90)
    rpath = pathlib.Path(str(base) + ".reply.json")
    rpath.write_text(r.stdout)
    try:
        reply = json.loads(r.stdout)
    except Exception:
        print("UNPARSEABLE REPLY (fail-closed). raw head:")
        print(r.stdout[:500])
        sys.exit(3)

    got = {}
    for q in ("risk_level", "run_now", "decision"):
        hits = walk_find(reply, q)
        got[q] = hits[0] if hits else None
    missing = [k for k, v in got.items() if v is None]
    if missing:
        print("REPLY MISSING ANSWERS:", missing, "- raw reply at", rpath)
        sys.exit(3)

    rl, rn, dec = got["risk_level"], got["run_now"], got["decision"]
    risk_score = rl.get("score")
    run_now = rn.get("noul")
    choice = dec.get("choice")
    probs = dec.get("probabilities") or {}
    p_choice = probs.get(choice)
    if p_choice is None:
        p_choice = dec.get("confidence")

    print("risk_level score:", risk_score,
          "| run_now p(true):", run_now,
          "| decision:", choice, "p:", p_choice)
    print("probabilities:", json.dumps(probs))

    ps = p_choice if p_choice is not None else 0.0
    rn_f = run_now if run_now is not None else -1.0
    rs = risk_score if risk_score is not None else 99
    if choice == "run" and ps >= 0.5 and rn_f >= 0.5 and rs <= 1.0:
        verdict = "RUN"
    elif choice == "block_and_fix":
        verdict = "BLOCK_AND_FIX"
    elif choice == "block_entirely":
        verdict = "BLOCK_ENTIRELY"
    else:
        verdict = "ASK_USER (mixed/low-confidence)"

    note = ""
    if extreme and verdict == "RUN":
        verdict = "BLOCK_AND_FIX"
        note = ("extreme-caution override: decider RUN suppressed "
                "(run p was %.3f)" % ps)
    elif extreme and verdict.startswith("ASK_USER"):
        verdict = "BLOCK_AND_FIX"
        note = "leaned on binary flags: unsure decider + extreme"

    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    tag = (args.tag + " ") if args.tag else ""
    line = "%s | %s%s%s | run=%s fix=%s never=%s | %s" % (
        date, tag, verdict, " [EXTREME]" if extreme else "",
        probs.get("run"), probs.get("block_and_fix"), probs.get("block_entirely"),
        sections["command"].splitlines()[0][:120])
    print("audit:", line)
    if note:
        print("note:", note)
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a") as f:
        f.write(line + "\n")
    sys.exit(0 if verdict == "RUN" else 1)


if __name__ == "__main__":
    main()
