---
name: decider
version: 1.1.1
description: "When Smart approval fires, ask the local decider server."
license: MIT
author: ais (enduserrr) + NoSleepHermes
metadata:
  hermes:
    tags: [approval, safety, decider, banana, local-model]
---

# Decider approval (local d1-2B decision model)

Substitutes the local decision server for the user when a command would trigger a
Smart-approval prompt. Server: llama-server `decide.service` on the decider host,
`http://127.0.0.1:9931/v1/systemone`.

## When to Use

- Load when the user asks for decider-backed approvals, stacks `/decider-approval`, or when
  you are about to run a command that Smart approval would surface to the user for consent.
- Skip for clearly safe, sandboxed, or reversible work — that path needs no approval.

## Hard rules

1. **Fail-closed, always.** Server down, timeout (`--max-time 45`), unparseable reply,
   conflicting answers, or confidence < 0.5 on the chosen option ⇒ ask the USER instead.
   Never let decider absence or noise enable a run.
2. **Honest state, no advocacy.** Fill `command_effects` neutrally and completely — every
   known side effect, including ones arguing against running. Never summarize away risk;
   if you cannot state the effects confidently, do not call the decider — ask the user.
3. `standing_policy` is included verbatim (template below), never reworded.
4. The user can always override a decider verdict by saying so.
5. **Keep the consult itself in an auto-approved shell shape.** Write the
   JSON payload to a file (file-writing tool), POST with `curl -d @file`
   from a script file, and parse the reply with a file-based script or
   plain text tools — never inline `python3 -c`/`-e`, and never PIPE
   anything into inline `python3 -c` (e.g. `curl … | python3 -c`): that
   shape raises a Smart-approval prompt that stalls ~10 minutes on
   silence, blocks the whole consult, and fails closed to the user anyway
   — the exact outcome `/decider-approval` exists to avoid. (Re-confirmed
   the hard way 2026-11-17: a curled HF API piped into inline python3 -c
   sat unanswered for the full 10-minute timeout.)
6. **The approval gate pattern-matches command TEXT, not effect.** Any
   terminal command whose string merely contains a flagged pattern (e.g.
   an `echo` log line quoting a recursive delete) triggers the same
   prompt. Keep log lines and payloads free of literal risky command
   text (say 'recursive delete of ...' instead), and append log lines via
   heredoc/file tools, not quoted echo.
7. **Consult PREEMPTIVELY when Smart approval is plausible.** The gate
   reliably fires on command classes that look routine — `systemctl --user
   restart/enable` of a service, process kills via pgrep/pidof expansion,
   env/config overwrites via redirection. An approval prompt that goes
   unanswered blocks the foreground call for ~10 minutes and then fails
   with 'silence is not consent'; the decider round-trip costs seconds.

## Procedure

When about to run a command that Smart approval would flag (risky/live-impacting), BEFORE
attempting it, POST once:

```bash
curl -s --max-time 45 http://127.0.0.1:9931/v1/systemone -H "Content-Type: application/json" -d '{
  "state": {
    "context": "An agent proposes running a shell command on the production host (banana).",
    "command": "<the exact command>",
    "command_effects": "<neutral full effects>",
    "tested": "<has this exact change been validated? where? if not: No + why>",
    "standing_policy": "Development must never impact anything in active use or depended on, including Hermes and the OS: develop/test only on mocks or COPIES of real files; only verified code touches real resources.",
    "blast_radius": "<what breaks if this goes wrong>",
    "alternative": "<safer path, or 'none'>"
  },
  "questions": {
    "risk_level": {"type": "score", "instructions": "How risky is running this command as-is?",
      "criteria": ["Safe — reversible or sandboxed", "Moderate — recoverable with effort", "High — likely damages the live system", "Critical — untested write to live state, whole system at risk"]},
    "run_now": {"type": "noul", "instructions": "Is it safe to run this command as-is, right now?"},
    "decision": {"type": "choice", "instructions": "What should the agent do with this command?",
      "criteria": {"run": "Run it as proposed.",
                   "block_and_fix": "Refuse; do the safer validation/backup path first, then re-ask.",
                   "block_entirely": "Never run this change at all."}}
  }
}'
```

Expected latency ~10 s per call (4-core CPU, single forward pass).

## Verdict mapping

| Answer | Action |
|---|---|
| `decision=run` (≥0.5) AND `run_now` ≥ 0.5 AND `risk_level.score` ≤ 1.0 | Run the command |
| `decision=block_and_fix` | Do NOT run. Perform its stated safer path (validate on a copy, take backup), then re-ask the decider with the updated state |
| `decision=block_entirely` | Do not run; do not retry variants of it; report refusal to user |
| Anything mixed / low-confidence / error / timeout | Ask the user |

Observed calibration (2026-11-04 tests): it approves sandboxed work (`run` 0.76) and
refuses even validated + backed-up live-DB swaps as-is (`block_and_fix` 0.79) — treat that
conservatism as intended behaviour: do the safer path, then re-ask with the updated state.

Report the verdict + probabilities to the user in the final answer when a command was
blocked or downgraded (auditability), e.g. `decider: block_and_fix 0.98 (run 0.002)`.

## Log

Append one line per verdict:
`~/.hermes/logs/decider-approval.log` — `<utc-date> | <verdict> | run=<p> fix=<p> never=<p> | <command, 120 chars>`.

## Guardian seat — already built; extend by config, not code

- The d1-2B is a DECISION-ONLY head: `/v1/chat/completions` and `/completion` on :9931 return 501 ("This model is a decision model without text generation, use /v1/systemone"). Never point a chat-completion client straight at the decider port — route it through the shim below.
- `~/.hermes/plugins/decider/guardian_shim.py` (systemd --user `decider-shim.service`, localhost:9932) IS the chat facade: parses the Hermes guardian prompt (`<command>` + `flagged as:`), answers one word APPROVE/DENY/ESCALATE from one batched `/v1/systemone` consult, 3-vote unanimity ensemble on high-impact classes, tuned thresholds (P_APPROVE 0.85 / CONF 0.70 / P_DENY 0.85). BEFORE writing any new decider-integration code, read that plugin's `PLUGIN-NOTES.md` — the seat exists, so wiring changes are `hermes config set` on `auxiliary.approval`, not new services (a duplicate shim just crash-loops on port 9932).
- Current wiring: default profile `auxiliary.approval` = {provider custom, model decider-guardian, base_url http://localhost:9932/v1, timeout 30} → every session reading default config (gateway Telegram/Discord turns, desktop, CLI) gets decider-answered smart approvals, ESCALATE→user only when stuck. A running gateway picks config changes up only after `hermes gateway restart`. The `decider` profile (`hermes -p decider config get approvals`) holds the reference block incl. the hard-deny list (sudo/su/doas/psql/mysql/systemctl --root/mkfs/dd if=/dev/shutdown/reboot) — replicate list changes deliberately, not by default.
- **Per-bot wiring is config, not a plugin.** Any profile gets decider-backed approvals by carrying the same `auxiliary.approval` block; check with `hermes -p <bot> config get auxiliary.approval`. Disabling the `decider` plugin in that profile (to drop its `decide` tool from a lean bot) does NOT touch approvals — the shim is a separate systemd --user service on :9932.
- **Verify a bot's approval path in one shot** instead of assuming the copy landed: write a guardian-shaped payload with a file tool and `curl -s -m 60 -d @file http://localhost:9932/v1/chat/completions` with a user message containing `<command>…</command>` and `flagged as: …`. Expect one word, APPROVE/DENY/ESCALATE, in ~2–5 s. `/v1/models` on :9932 returns 404 — the shim implements only the chat route, so a 404 there is not a health signal.

## Ops

- Endpoint reachability from the agent's own shell: the listener may not answer on `hostname -I`'s addresses, and hostname aliases can fail to resolve — connect via loopback first; if refused, find the real bind with `ss -tlnp | grep 9931` and POST to that IP. Reply JSON paths: `answers.risk_level.score`, `answers.run_now.noul`, `answers.decision.choice`; a body missing `state` or `questions` 400s with `"state\" must be provided"`.
- Health: `curl -s http://127.0.0.1:9931/health`
- Logs/restart: `journalctl --user -u decide -f` / `systemctl --user restart decide` (unit renamed from iota-decide.service, 2026-11-11)
- Model: **d1-2B Q4_K_M** (`~/models/d1-2B-Q4_K_M.gguf`, LFM3-VL lineage; swapped in for
  the retired iota-decide-4b on 2026-11-05 — on the 231-question JevBench public split,
  d1-2B Q4_K_M scored 79.7% vs the predecessor Q4_K_M's 78.4% (181/231 per its card),
  at 4× smaller). Launcher `~/applications/llama.cpp/start-decider.sh` (the source host
  kept its old `start-iota-server.sh` filename and a legacy unit-name slot).
- Latency: ~1-2 s typical, up to ~40-100 s on very long states (CPU).
- Banana-only: from any other host 127.0.0.1:9931 is unreachable ⇒ fail-closed to user.
