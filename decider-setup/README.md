# Local decider for Hermes smart approvals — setup & operations

Shareable snapshot of the live deployment, prepared 2026-11-17. **Sanitized:** no
addresses, tokens, keys, or chat IDs. Everything assumes loopback (`127.0.0.1`) —
the decider host and the Hermes host are the same machine. If you split them across
hosts, bind to a tailnet/LAN address and keep both ports off all-interfaces binds.
The deployment machine here is a 4-core / 8 GB CPU-only mini-PC; nothing needs a GPU.

```
Hermes agent turn
  └─ smart-approval gate fires on a risky command
       ├─ wired mode (default): Hermes POSTs guardian prompt → guardian shim :9932
       │     └─ shim parses <command> + "flagged as:" → ONE /v1/systemone consult
       │          → one word: APPROVE / DENY / ESCALATE  (ESCALATE → asks the user)
       └─ skill mode: agent loads the `decider` skill and consults :9931 itself,
          preemptively, before the gate stalls on an unanswered prompt
                    both sit on top of ↓
       llama-server (decide.service) :9931  —  d1-2B Q4_K_M decision model
```

Two usage modes, both documented below:

1. **Skill mode** — the `decider` skill (copy in `decider-approval/`) makes the agent
   consult the decider *before* commands that Smart approval would flag, so the
   consult costs seconds instead of a ~10-minute silent-gate stall.
2. **Wired mode (the gateway default)** — every session reading the profile config
   (desktop, CLI, Telegram/Discord gateway turns) gets smart approvals *answered*
   by the shim via `auxiliary.approval`. No per-command agent action needed;
   `ESCALATE` is the only path back to a human.

Fail-closed everywhere: server down, timeout, unparseable reply, conflicting answers,
or low confidence ⇒ the user is asked. Never let decider absence enable a run.

## Bundle contents

| Path | What |
|---|---|
| `README.md` | this document |
| `BENCHMARKING.md` | how to benchmark the stack (smoke → probes → public eval → swap protocol) |
| `decider-approval/SKILL.md` | sanitized copy of the `decider` skill — install into the other instance's skills tree |
| `plugin-decider/` | sanitized source of the Hermes plugin: guardian shim, decider client/registry, delegation gate, CLI scripts, tests |
| `systemd/` | `decide.service`, `decider-shim.service`, `start-decider.sh` (drop-in units, `%h`-based paths) |
| `benchmark/` | `probes.jsonl` + `bench_decider.py` — self-contained end-to-end bench (stdlib only) |

## Requirements

- Linux + systemd (user units), Python 3 (stdlib only — the shim and bench need no pip packages).
- **llama.cpp build ≥ b11960 (v0.8.0)** — that's when decision-model serving (`/v1/systemone`,
  one constrained forward pass, no token generation) landed. Newer is fine; the reference
  deployment runs b12001, CPU-only.
- ~1.3 GB RAM for the model at Q4_K_M, plus llama-server overhead.
- Hermes with the smart-approval feature (`approvals.mode smart`); gateways (Telegram/Discord)
  read the same profile config.

## 1. Model

| | |
|---|---|
| Repo | https://huggingface.co/LiquidAI/d1-2B-GGUF (base: https://huggingface.co/LiquidAI/d1-2B) |
| File in use | `d1-2B-Q4_K_M.gguf` — direct: https://huggingface.co/LiquidAI/d1-2B-GGUF/resolve/main/d1-2B-Q4_K_M.gguf |
| Quant in use | **Q4_K_M, 1.10 GB** (repo also ships BF16 / F16 / Q4_0 / Q8_0 and `mmproj-*` multimodal projectors — the projector is unused in this deployment) |
| sha256 | `adca5789ad30ae6027e8e936749bb9f19673097492ab26fa1c5b69643ca50b4b` |
| Lineage | LiquidAI **d1-2B**, fine-tune of `LFM3-VL-2B` — a *decision model*: returns typed answers (choice/score/noul) with calibrated probabilities in **one forward pass**, no generation. `/v1/chat/completions` and `/completion` return **501** — it is not a chat model. |
| Role history | Swapped in for the retired 4B predecessor (iota-decide-4b) on 2026-11-05. Comparison ran on the **231-question JevBench public split** (the board's long-standing published set; swap-time notes tagged the then-current method v1.5 — the frozen v1.5 method's own open set is larger: 904 open + 720 sealed = 1,624 decisions): d1-2B Q4_K_M **79.7%** vs predecessor Q4_K_M **78.4%** (181/231 per its card; its bf16 number is 182/231 = 78.8%), at **4× smaller** size. Replay the 231-task split yourself with `benchmark/bench_decider.py --tasks`. |
| Newer options | LiquidAI announced `d1.2` / `d1.2-ultra` (~2026-11-16, audio support, five new tasks) — no GGUF on HF at the time of writing, so not evaluated here. A bigger sibling `LiquidAI/d1-3B-GGUF` exists if you want to trade RAM/latency for accuracy; benchmark before swapping (see `BENCHMARKING.md`). |

Download + verify:

```bash
mkdir -p ~/models
curl -L -o ~/models/d1-2B-Q4_K_M.gguf \
  https://huggingface.co/LiquidAI/d1-2B-GGUF/resolve/main/d1-2B-Q4_K_M.gguf
sha256sum ~/models/d1-2B-Q4_K_M.gguf   # must match the hash above
```

## 2. llama-server — the decision endpoint (:9931)

Build llama.cpp ≥ b11960 per its upstream README (plain CPU build is fine), then put the
`llama-server` binary on PATH (reference deployment: `~/.local/bin/llama-server`).

Launcher — `systemd/start-decider.sh` in this bundle (live name on the source host:
`start-iota-server.sh`):

```bash
#!/usr/bin/env bash
exec "$HOME/.local/bin/llama-server" \
  -m "$HOME/models/d1-2B-Q4_K_M.gguf" \
  -b 8192 -ub 8192 \
  --host 127.0.0.1 --port 9931
```

`-b 8192 -ub 8192` makes the model read the whole (potentially long) decision input in one
pass. Loopback bind + no API key is the intended posture; if you ever open the bind, add
`--api-key <key>` and mirror it in clients.

Unit — `systemd/decide.service`:

```ini
[Unit]
Description=d1-2B Q4_K_M decision model (llama-server on 127.0.0.1:9931)
After=network-online.target

[Service]
ExecStart=%h/applications/llama.cpp/start-decider.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Install and verify (the bundle assumes `~/.local/bin/llama-server` exists — check
`~/.local/bin/llama-server --version` reports a build ≥ b11960, else build per upstream first;
an older build silently lacks `/v1/systemone` and every consult fails):

```bash
mkdir -p ~/applications/llama.cpp ~/.config/systemd/user
install -m 755 systemd/start-decider.sh ~/applications/llama.cpp/start-decider.sh
cp systemd/decide.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now decide
loginctl enable-linger "$USER"   # MANDATORY on unattended gateway hosts: without linger,
                                 # user units die at logout/reboot and approvals fail closed
curl -s http://127.0.0.1:9931/health          # → {"status":"ok"}
journalctl --user -u decide -f                # logs
```

Smoke-test the decision endpoint (this shape — a `state` plus typed `questions` — is the
whole API; missing `state`/`questions` ⇒ HTTP 400):

```bash
curl -s --max-time 45 http://127.0.0.1:9931/v1/systemone -H "Content-Type: application/json" -d '{
  "state": {"text": "A service unit file was edited and needs a user-scope restart."},
  "questions": {"go": {"type": "noul", "instructions": "Restarting a systemd --user unit now is safe.",
                       "criteria": {"true": "safe", "false": "unsafe"}}}
}'
# → {"answers": {"go": {"type": "noul", "noul": 0.99}}, ...}   (noul = p(true))
```

Reply JSON paths: noul-type questions answer under `answers.<qname>.noul` (a single
`p(true)`; `{"type": "noul", "noul": 0.99}`), choice/score questions under
`answers.<qname>.choice` / `.score` plus `.probabilities` and `.confidence`. A body missing
`state` or `questions` ⇒ HTTP 400. Typical latency 1–2 s on short states (full skill-mode
consults with long state/effects text run ~10 s); up to ~40–100 s only on pathologically
long states (CPU).

## 3. Guardian shim — the approval facade (:9932)

`plugin-decider/guardian_shim.py` is what makes wired mode work. Hermes's smart-approval
pipeline calls it as an OpenAI-compatible chat endpoint and it answers exactly one word:

- Parses the guardian prompt (`<command>…</command>` + `flagged as: …`).
- Unparseable prompt ⇒ **ESCALATE**; decider unreachable ⇒ **HTTP 500** (Hermes escalates).
- Thresholds: APPROVE needs `p(approve) ≥ 0.85` and confidence `≥ 0.70`; DENY needs
  `p(deny) ≥ 0.85`; anything else ⇒ ESCALATE.
- High-impact command classes (recursive deletes, disk/fs ops, fork-bombs, shutdown/reboot,
  system-scope systemctl, package installs, force-pushes, …) run a **3-vote ensemble with
  paraphrased instructions; unanimity required**, else ESCALATE.
- (command, description) LRU cache (512 entries); decision log
  `~/.hermes/plugins/decider/data/shim-decisions-YYYYMM.jsonl`; `GET /health` works;
  `/v1/models` is a 404 **by design** — only the chat route exists, so don't use it as a
  health signal.

Install (the bundle copy already has registry + client + CLI scripts + tests):

```bash
cp -r plugin-decider ~/.hermes/plugins/decider
chmod +x ~/.hermes/plugins/decider/scripts/decide*   # archive extraction can drop exec bits
hermes plugins validate                     # should pass (if your build lacks this subcommand:
                                            # `hermes plugins --help`, then just confirm the
                                            # plugin dir is registered)
python3 -m unittest discover -s ~/.hermes/plugins/decider/tests   # optional sanity
# NOTE: the shim tests write MOCKED rows into ~/.hermes/plugins/decider/data/shim-decisions-*.jsonl
# (the audit log you'll later mine for tuning) — run tests before go-live, or delete that
# month's file afterwards.
```

**Before enabling wired mode — adapt the shim's machine policy (mandatory).** The shipped
`guardian_shim.py` hardcodes the reference host's facts into every approval consult
(`_QUESTION.instructions`, ~line 61: "Debian, user 'hermes', no sudo exists, podman is
rootless, systemctl --user is fine"; `_BANANA_POLICY` ~line 53 is dead text). Rewrite both to
the TARGET machine's real facts — a box **with** sudo, Docker instead of podman, or a
different username otherwise gets approvals reasoned from false policy. Locate with
`grep -n "no sudo exists\|rootless" ~/.hermes/plugins/decider/guardian_shim.py`.

```bash
cp systemd/decider-shim.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now decider-shim
curl -s http://127.0.0.1:9932/health
```

Verify the approval path end-to-end (expect one word in ~2–5 s):

```bash
printf '%s' '{"model":"decider-guardian","messages":[{"role":"user","content":"<command>python3 --version</command>\nflagged as: version check"}]}' \
  > /tmp/guardian-probe.json
curl -s -m 60 -d @/tmp/guardian-probe.json http://127.0.0.1:9932/v1/chat/completions
# → {"choices":[{"message":{"content":"APPROVE"...}}]}
```

## 4. Hermes wiring

### Wired mode — default profile (desktop, CLI, Telegram/Discord gateways)

Set on the profile the gateways run under (reference deployment uses the default profile):

```bash
hermes config set approvals.mode smart
hermes config set auxiliary.approval.provider custom
hermes config set auxiliary.approval.model decider-guardian
hermes config set auxiliary.approval.base_url http://127.0.0.1:9932/v1
hermes config set auxiliary.approval.api_key ''
hermes config set auxiliary.approval.timeout 30   # >30 s consults (long-state tail, §2) time
                                                  # out and escalate — fail-closed by design;
                                                  # raise consciously only on a slow box
# safe defaults for unattended contexts:
hermes config set approvals.cron_mode deny
hermes config set approvals.single_query_mode deny
hermes config set approvals.unattended_mode deny
```

Equivalent YAML shape:

```yaml
# timeout: 600 and denial_breaker_threshold: 3 are Hermes defaults, shown for completeness —
# pin them explicitly only if you want them versioned in config
approvals:
  mode: smart
  timeout: 600
  cron_mode: deny
  single_query_mode: deny
  unattended_mode: deny
  denial_breaker_threshold: 3
auxiliary:
  approval:
    provider: custom
    model: decider-guardian
    base_url: http://127.0.0.1:9932/v1
    api_key: ''
    timeout: 30
```

**A running gateway picks config changes up only after `hermes gateway restart`.**

Optional hard-deny list (never delegated to the model, always user/gate): the reference
`decider` profile carries `sudo *`, `su *`, `doas *`, `psql*`, `mysql*`, `systemctl * --root*`,
`mkfs*`, `dd if=/dev/*`, `shutdown*`, `reboot*` under `approvals.deny`. Replicate
deliberately, not by default.

Per-bot profiles work the same way — the wiring is config, not a plugin: carry the same
`auxiliary.approval` block (`hermes -p <bot> config set …`; check with
`hermes -p <bot> config get auxiliary.approval`). Disabling the `decider` plugin in a
lean profile (to drop its `decide` tool) does **not** touch approvals — the shim is an
independent service on :9932.

### Skill mode — install the skill

```bash
mkdir -p ~/.hermes/skills/hermes-ops
cp -r decider-approval ~/.hermes/skills/hermes-ops/decider-approval
# skim the copied SKILL.md for source-host specifics to adapt: the consult template's
# context line names the source host ("banana"), its Ops section assumes that host's
# reachability, and tags carry the same name — reword to the target machine.
```

The skill teaches the agent to consult `/v1/systemone` **preemptively** whenever Smart
approval is plausible (gate reliably fires even on routine-looking `systemctl --user`
restarts, kills, and config overwrites — and an unanswered gate blocks ~10 minutes then
fails with "silence is not consent"). Keep its hard rules intact: fail-closed, honest
neutral `command_effects`, verbatim standing policy, consult via script-file + `curl -d @file`
shapes (inline `python3 -c`/pipes into it raise the very approval prompt you're avoiding).

### Verify the wiring

```bash
hermes config get approvals
hermes config get auxiliary.approval
hermes approvals test        # interactive self-test of the approval pipeline
```

Then from a gateway chat: run something benign-but-flagged and watch it get answered by the
shim (`data/shim-decisions-*.jsonl` grows; ESCALATEs surface to you in-chat).

## 5. Day-2 operations

- **Logs:** decider `journalctl --user -u decide -f`; restart `systemctl --user restart decide`.
  Shim decisions: `~/.hermes/plugins/decider/data/shim-decisions-YYYYMM.jsonl`; shim log
  likewise `-u decider-shim`.
- **Tuning:** if production ESCALATE-rate is too high, mine the shim JSONL and lower
  `P_APPROVE/CONF_APPROVE` (`0.85/0.70` were themselves lowered from `0.90/0.75` after live
  probes). Recalibrate from data, not vibes; the ensemble unanimity rule is the safety floor.
- **Model swaps:** edit `-m` in the start script, `systemctl --user restart decide`; keep the
  old GGUF on disk for one-line revert. Bench first — see `BENCHMARKING.md`.
- **Port hygiene:** never point a chat-completion client at :9931 (decision-only model ⇒ 501);
  route everything through the shim.
- **Plugin extras:** the plugin also provides a `decide` tool for agents, a CLI
  (`scripts/decide --list-models`), and a user-armed delegation gate (`scripts/decide-session`,
  REFUSED until armed; arming is user-only) for decider-backed approvals of delegated
  subagents. All optional.
- **Deviations from this doc's loopback assumption:** if the decider listener doesn't answer on
  loopback, find the real bind with `ss -tlnp | grep 9931` and POST to that address.

*Snapshot provenance: `ais (enduserrr) + NoSleepHermes`, 2026-11-17, from the live deployment
(`decide.service` d1-2B Q4_K_M + the guardian shim, Hermes default-profile wiring). This bundle
renames the legacy `iota-*` identifiers — `iota-guardian-shim.service` → `decider-shim.service`,
plugin `iota-decider` → `decider`, registry key `iota-decide-4b` → `d1-2b`, chat-model label
`iota-guardian` → `decider-guardian` — because the iota model is retired; the source host still
runs the legacy names. The live plugin dir also carries a `QUESTBOOK.md` dev log — excluded
from this bundle.*
