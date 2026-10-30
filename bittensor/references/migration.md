# Migrating Bittensor SDK code to v10 (from older v9)

Companion to the `bittensor` skill. Read this **before editing any file** when
bringing v9-era code up to the v10 SDK. The official migration reference —
with the full old↔new mapping tables for every scripted call and CLI command —
lives at:
`https://www.bittensor.com/llms.mdx/docs/migration/content.md`
(fetch it with curl; every section is exact, not illustrative).

## Migration workflow

1. **Read any handoff/migration doc first** (e.g. `MIGRATION_STATUS.md`) and
   honor its hard constraints. Typical constraint: fix ONE file, smoke-test,
   **STOP, ask the user** before touching the next. Keep a changelog table of
   every edit: file, line, issue, fix, why.
2. **Never trust migration docs, memory, or blog posts over the *installed*
   library.** Verify every API against installed source under
   `<venv>/site-packages/bittensor/` (and `bittensor_wallet/`) before editing:
   signatures, dataclass fields, accepted kwargs. Handoff docs can be wrong or
   stale — source inspection has repeatedly settled disputes.
3. Verify reads live (public chain data needs no wallet). **Never submit real
   transactions during testing** — exercise mutations against a testnet
   endpoint (`--network test`) or a dedicated throwaway wallet with a tiny
   balance, never the user's main funds.
4. Run the repo's unit tests **before AND after** edits. Test fixtures usually
   need the same treatment as production code (e.g. mocked stake/balance
   objects must use the real SDK classes, not plain ints).
5. Test runs needing settings env vars without a real wallet: pass dummy
   values inline (`WALLET_PW=x WALLET_NAME=y python3 -m unittest ...`).

## Environment layout (v10-era)

| Component | Package | Notes |
|---|---|---|
| SDK | `bittensor` 10.x | `Subtensor` class (~165 methods), sync + async variants |
| CLI | `bittensor-cli` 9.x (separate package, ships `btcli`) | independent version line from the SDK |
| Wallet | `bittensor_wallet` (separate package) | keyfiles are version-compatible; nothing to convert |
| Python | 3.10+ | |
| Config | `~/.bittensor/config.yml` | wallets default to `~/.bittensor/wallets/` |

Pin discipline: `requirements.txt` carries BOTH packages with explicit pins
(`bittensor==`, `bittensor-cli==`) — they version independently, so an
unpinned CLI can drift under a pinned SDK.

## Version-drift traps (hard-won)

- **Same call name, different data shape underneath.** 10.4→10.5 silently
  reworked the price read path (`get_subnet_prices()` now served via
  `SwapRuntimeApi.current_alpha_price*`). An additive changelog/wheel diff
  does NOT prove behavioral compatibility — diff the actual wheels when
  answering "newest version my code survives on".
- **Warning fingerprints identify the SDK version, not the bug.**
  `Unable to fetch subnet prices for block None, block hash None` = a
  pre-10.5 SDK process querying the removed `Swap.AlphaSqrtPrice` storage
  item — even when the visible code looks unrelated. Error strings often
  exist in BOTH `subtensor.py` and `async_subtensor.py` with slightly
  different formats (the `block None, block hash None` variant is the async
  one); grep installed site-packages across ALL venvs first.
- **Loose result handling compiles everywhere.** `float(balance_obj)` and
  `if result is True:` work on v10 but are the exact patterns later majors
  remove — when touching such lines anyway, prefer explicit conversions and
  result-object checks so the code survives the next upgrade.
- **`subnets.all()` is NOT the old `all_subnets()`** — it lacks price/pool
  reserves; use the runtime API (`SubnetInfoRuntimeApi.get_all_dynamic_info`)
  when prices are needed.

## btcli (v9) surface for scripts/automation

- Reads first: every command supports `-h`; machine-readable output via
  `--json-output` / `--json-out` (also `--json-out <file>` styles on some
  commands — check `-h` per command).
- Non-interactive runs: `--yes` / `--no-prompt` skips confirmations. Without a
  TTY and without it, expect a prompt failure, not a hang — always pass it in
  scripts.
- Global options: `--wallet.name/--wallet-name/--name`, `--wallet.hotkey/
  --hotkey/-H`, `--wallet.path/-p`, network via `--network` /
  `--subtensor.network` / `--chain` / `--subtensor.chain_endpoint`.
- Group shorthands are first-class: `w` (wallet), `st` (stake), `s` (subnets),
  `su` (sudo), `c` (config), `wt` (weights) — scripts in the wild use them.
- Destination options (`--dest`, `--hotkey`, ...) accept raw ss58, address-book
  names, or local key names (`WALLET/HOTKEY`); destinations never default.
- Groups seen in real repos: `wallet` (list/create/new-coldkey/new-hotkey/
  regen/balance/transfer/overview/inspect/swap-hotkey/set-identity/history),
  `stake` (add/remove/list/move/transfer/swap/auto/child/claims), `subnets`
  (list/show/metagraph/register/burn-cost/price), `sudo` (set --param/--value,
  get, take, trim), `weights commit/reveal`, `axon` serve, `proxy`, `utils
  convert`.
