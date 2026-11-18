#!/usr/bin/env python3
"""bench_decider.py — end-to-end benchmark for a local decider stack (stdlib only).

Two modes:

  --probes FILE   Guardian-shaped probes through the guardian shim (:9932), exactly
                  the path Hermes's smart-approval pipeline takes. Reports the verdict
                  (APPROVE/DENY/ESCALATE), latency, and agreement with the advisory
                  `expect` labels in probes.jsonl.

  --tasks FILE    JevBench-style public task JSONL straight to llama-server's
                  /v1/systemone (:9931). Scores argmax label vs the task's `expected`
                  field. Reports accuracy overall/per-type plus latency percentiles.
                  Use for candidate-vs-incumbent A/B under an identical harness.

Fail-closed accounting: transport errors and unparseable answers count as WRONG and are
reported separately — never dropped. Exit code is always 0; this tool is advisory.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

NAMES = {"approve": "APPROVE", "deny": "DENY", "escalate": "ESCALATE"}


def post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


# ---------------------------------------------------------------- probes mode

def run_probes(args) -> None:
    rows = [json.loads(l) for l in open(args.probes, encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    url = args.shim_url.rstrip("/") + "/v1/chat/completions"
    dist: dict[str, int] = {}
    latencies, agree, mismatches, errors = [], 0, [], 0
    for row in rows:
        content = f"<command>{row['command']}</command>\nflagged as: {row.get('flagged_as', '')}"
        t0 = time.perf_counter()
        try:
            out = post(url, {"model": "decider-guardian",
                             "messages": [{"role": "user", "content": content}]},
                       timeout=args.timeout)
            word = str(out["choices"][0]["message"]["content"]).strip().split()[0].upper()
            lat = time.perf_counter() - t0
            latencies.append(lat)
        except Exception as e:  # noqa: BLE001
            word, lat, errors = f"ERROR:{type(e).__name__}", time.perf_counter() - t0, errors + 1
        dist[word] = dist.get(word, 0) + 1
        mark = ""
        if row.get("expect") and word == row["expect"]:
            agree += 1
        elif row.get("expect"):
            mark = "  <-- expected " + row["expect"]
            mismatches.append(row["command"])
        print(f"  {word:<12} {lat:6.2f}s  {row['command'][:70]}{mark}")
    n = len(rows)
    print(f"\nprobes: {n}  agreement: {agree}/{n}  errors: {errors}")
    print("verdict distribution:", dict(sorted(dist.items())))
    if latencies:
        print(f"latency s: p50={pct(latencies, .5):.2f} p95={pct(latencies, .95):.2f} "
              f"mean={statistics.mean(latencies):.2f}")
    if mismatches:
        print("advisory mismatches (review, not failures):", *mismatches[:10], sep="\n  ")


# ----------------------------------------------------------------- tasks mode

def normalize_criteria(qtype: str, criteria):
    # score questions keep their criteria as a LIST of level texts (llama.cpp maps
    # levels itself and answers with .score + probabilities over "0".."k");
    # converting to a dict 400s.
    if isinstance(criteria, (dict, list)):
        return criteria
    if qtype == "noul":
        return {"true": "Yes", "false": "No"}  # sg-adapter-style fallback when a task ships none
    return {}


def expected_label(qtype: str, expected, labels: list[str]) -> str:
    return str(expected)


def run_tasks(args) -> None:
    rows = [json.loads(l) for l in open(args.tasks, encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    url = args.url.rstrip("/") + "/v1/systemone"
    per_type: dict[str, list[int]] = {}
    latencies, errors, shown = [], 0, 0
    for task in rows:
        q = task["question"]
        qtype = q["type"]
        body = {"state": task["state"],
                "questions": {"decision": {"type": qtype,
                                           "instructions": q["instructions"],
                                           "criteria": normalize_criteria(qtype, q.get("criteria"))}}}
        t0 = time.perf_counter()
        try:
            out = post(url, body, timeout=args.timeout)
            ans = out["answers"]["decision"]
            lat = time.perf_counter() - t0
            latencies.append(lat)
        except Exception as e:  # noqa: BLE001
            if shown < 5:
                print(f"  transport error: {type(e).__name__}: {e}", file=sys.stderr)
                shown += 1
            errors += 1
            stats = per_type.setdefault(qtype, [0, 0])
            stats[1] += 1
            continue
        # noul answers carry a single p(true) under `.noul`; choice/score carry a
        # probability distribution under `.probabilities`
        if qtype == "noul" and isinstance(ans.get("noul"), (int, float)):
            p_true = float(ans["noul"])
            probs = {"yes": p_true, "no": 1.0 - p_true}
        else:
            probs = {str(k): float(v) for k, v in (ans.get("probabilities") or {}).items()}
        if probs:
            pred = max(probs, key=probs.get)
            if qtype == "noul":  # criteria keys true/false <-> expected yes/no
                pred = {"true": "yes", "false": "no"}.get(pred, pred)
        elif ans.get("choice") is not None:
            pred = str(ans["choice"])
        else:
            pred = None
        exp = expected_label(qtype, task.get("expected"), task.get("labels") or [])
        ok = pred is not None and pred == exp
        stats = per_type.setdefault(qtype, [0, 0])
        stats[0 if ok else 1] += 1
        if not ok and shown < 15:
            top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
            print(f"  miss [{qtype}] expected={exp!r} pred={pred!r} top={top}")
            shown += 1
    total_r, total_w = 0, 0
    print(f"\ntasks: {len(rows)}  transport errors: {errors}")
    for qtype, (right, wrong) in sorted(per_type.items()):
        total_r, total_w = total_r + right, total_w + wrong
        n = right + wrong
        print(f"  {qtype:<7} {right}/{n} = {right / n:.1%}" if n else f"  {qtype:<7} n/a")
    if total_r + total_w:
        acc = total_r / (total_r + total_w)
        print(f"  TOTAL   {total_r}/{total_r + total_w} = {acc:.1%}")
    if latencies:
        print(f"latency s: p50={pct(latencies, .5):.2f} p95={pct(latencies, .95):.2f} "
              f"mean={statistics.mean(latencies):.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--probes", help="probe JSONL -> guardian shim mode")
    ap.add_argument("--tasks", help="JevBench-style task JSONL -> /v1/systemone mode")
    ap.add_argument("--url", default="http://127.0.0.1:9931",
                    help="decider base URL for --tasks (gets /v1/systemone appended)")
    ap.add_argument("--shim-url", dest="shim_url", default="http://127.0.0.1:9932",
                    help="guardian shim base URL for --probes (gets /v1/chat/completions appended)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=120.0, help="per-request timeout s")
    args = ap.parse_args()
    if bool(args.probes) == bool(args.tasks):
        ap.error("choose exactly one of --probes / --tasks")
    if args.probes:
        run_probes(args)
    else:
        run_tasks(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
