# plugin-decider — bundle notes

Sanitized source copy of the Hermes plugin that backs the local decider
(snapshot 2026-11-17). **Naming:** this bundle drops the legacy `iota-*` prefixes —
unit `decider-shim.service` (was `iota-guardian-shim.service`), plugin `decider`
(was `iota-decider`), registry key `d1-2b` and chat-model label `decider-guardian`
(were `iota-decide-4b` / `iota-guardian`). The source host still runs the legacy
names; the retired 4B predecessor `iota-decide-4b` keeps its name only in history
notes. Install and wiring instructions live in `../README.md`
(sections 3–4); benchmarking in `../BENCHMARKING.md`.

## Included

| File | Role |
|---|---|
| `guardian_shim.py` | The guardian seat: OpenAI-chat facade on :9932 that Hermes's smart-approval pipeline calls; translates the guardian prompt into one batched `/v1/systemone` consult; answers APPROVE/DENY/ESCALATE; 3-vote unanimity ensemble on high-impact classes; thresholds `P_APPROVE 0.85 / CONF_APPROVE 0.70 / P_DENY 0.85`. |
| `decider_client.py` | Registry + transport adapters (`systemone`, `openai_chat`), hash caching, failure contract `{"ok": false, "error": ...}` — never a guessed verdict. |
| `models.json` | Model registry — key `d1-2b` → `localhost:9931` `/v1/systemone`, serving LiquidAI d1-2B Q4_K_M. Renamed from the legacy `iota-decide-4b` key in this bundle; the retired 4B predecessor keeps its name only in history notes. |
| `plugin.yaml`, `__init__.py` | Hermes plugin manifest; provides the optional `decide` tool. |
| `scripts/decide` | CLI: `--template`, `--questions-file`, `--list-models`; exit 3 on transport/parse error. |
| `scripts/decide-admin`, `delegation_gate.py`, `scripts/decide-session` | User-owned delegation gate for decider-backed approval of delegated subagents. Default REFUSED, fail-closed on corrupt/missing state; arming is user-only (`decide-session` refuses without the gate (exit 3) or without a `decider` profile (exit 4); `--dry-run` prints the launch command). |
| `templates/command-safety.json` | v1 safety-screen question template. |
| `tests/` | unittest suites (client, gate, plugin, shim). |

## Not included (exists only in the live deployment)

- `data/` — runtime logs (`shim-decisions-YYYYMM.jsonl`, delegation state). Created on
  first run; **contains real command history — never sync it anywhere.**
- `__pycache__/`
- `QUESTBOOK.md` — the plugin's dev-session log (entry/status protocol). Read it before
  changing wiring on the live host; internal history, kept out of the share.

## Expectations

- Shim is localhost-only by design; systemd unit in `../systemd/`.
- `GET /health` answers; `/v1/models` is intentionally 404 (only the chat route exists).
- Parse failure ⇒ ESCALATE (HTTP 200); decider unreachable ⇒ HTTP 500 (Hermes escalates).
- The machine-policy text baked into the shim's question template describes the reference
  host (Debian, no sudo, rootless podman, `systemctl --user` fine) — adjust it to the
  target machine's facts before relying on wired approvals there.
