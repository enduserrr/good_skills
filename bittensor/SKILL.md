---
name: bittensor
version: 2.0.0
author: ais + NoSleepHermes
license: MIT
metadata:
  hermes:
    tags: [bittensor, TAO, crypto, trading, sdk-migration]
    related_skills: []
description: Use for Bittensor SDK/CLI work, on-chain Bittensor research, bots, staking, migrations.
---

# Bittensor SDK Work

Targets the bittensor SDK v10 line (with the separate `bittensor-cli` v9
`btcli`). For bringing older v9 code forward, read
`references/migration.md` first.

## When to Use

- Any Bittensor project: subnet, dTAO, bittensor SDK, bittensor-cli, staking
  tools, chain queries.
- Writing/reviewing code calling `bittensor`, `btcli`, or touching TAO/alpha
  balances, stake operations, or subnet data.
- Driving `btcli` from scripts/automation (JSON output, non-interactive
  confirmation) or discovering the API surface at runtime.
- **Migrating code from older v9 to v10** → **read `references/migration.md`
  first**, before editing any file.

## Migration? Start there, not here

Migrating v9-era code to the v10 SDK is covered in **`references/migration.md`**:
the file-by-file workflow and its stop-and-ask gate, the environment layout
(SDK / CLI / wallet are three packages with independent version lines), and
the version-drift traps (same call name, different data shape; warning
fingerprints that identify the SDK version; loose result handling).

Two rules from that doc that apply to **all** Bittensor work, not just
migrations:

- **Never trust docs, memory, or blog posts over the *installed* library.**
  Verify signatures, dataclass fields, and accepted kwargs against
  `<venv>/site-packages/bittensor/` (and `bittensor_wallet/`) before you rely
  on them. When no local environment has bittensor installed, the fresh docs
  clone (below) is the source of record — state that basis in the answer
  instead of guessing signatures.
- **Before arithmetic on any chain value, verify its unit and definition** in
  the docs (`llms-full.txt`) or chain source — rao vs TAO vs alpha, and
  similarly-named fields with different meanings. Compose conversions
  explicitly and show the spot price used.
- **NEVER submit real trades during testing.** Verify reads live (public chain
  data needs no wallet); exercise any mutation on a testnet endpoint
  (`--network test`) or a dedicated throwaway wallet with a tiny balance —
  never the user's main funds.

## Docs access (agent-first — start here, and use it LIBERALLY)

**Consult the docs before answering ANY Bittensor factual question you are not
100% certain about — domain concept, term/definition, unit, storage item,
extrinsic, hyperparameter, or fee/economics rule — and whenever a mistake
would be costly (money, weights, misreported chain state).** This prevents
real classes of error: unit mistakes (`locked_mass` is ALPHA, not TAO;
`alpha_market_cap_tao` vs `alpha_fdv_tao`), conflating stage-1 price share
with TAO emission share, misreading epoch provenance (incentive reflects the
last COMPLETED tempo), and trusting stale memory over chain/runtime changes.
If a term or number would appear in your final answer and you cannot cite
where you verified it, that is the trigger to check the docs — then the chain.
When in doubt, check; the docs are cheap, wrong answers are not.

### Primary: local docs clone (start here — no network needed)

A sparse git clone of the official docs source (RaoFoundation/subtensor,
`docs/` tree), refreshable by script:

- **Location:** `~/.hermes/cache/subtensor-docs/docs/` — grep/read it directly
  (`search_files`, `read_file`, `rg`). Contains: `sdk.mdx` (SDK surface),
  `cli.mdx` (btcli), `query/` and `tx/` (reads and transactions, one page
  each), `concepts/` (domain definitions: money, emissions, consensus,
  dTAO...), `errors/` (error semantics), `hyperparameters/`, `guides/`,
  `internals/`, `migration.mdx`.
- **Freshness:** `git -C ~/.hermes/cache/subtensor-docs log -1 --format=%ci`
  shows the commit date; force-refresh any time with
  `scripts/update-bt-docs.sh` next to this SKILL.md (safe, idempotent;
  schedule it from cron).
- **Feature/release research → the release guide first.** Runtime releases
  ship a complete release note under `guides/<release>.mdx` — one page with
  the full new surface: new extrinsic(s) (pallet + allowed signer), storage
  items, events, runtime API, EVM precompiles, btcli commands, migration
  names, deprecations, and the chain-source file paths. For "what is X / how
  is X set and queried / which PR" questions, read that guide before
  assembling the same picture from `tx/`/`query/` fragments, then confirm
  PR/merge metadata on GitHub: `gh pr list --repo RaoFoundation/subtensor
  --search '<kw> in:title merged:>=<date>'`, `gh pr view N --json
  title,mergedAt,commits,body`, and per-file commit history via
  `gh api 'repos/RaoFoundation/subtensor/commits?path=<path>'`.
- **Concept definitions, term/unit questions, SDK calls, btcli flags, error
  meanings → search this clone FIRST.** Only fall back to the live URLs below
  for things the clone can't answer (JSON op catalogs, chain source search)
  or if the clone looks stale.

### Fallback: live web docs

Docs are built to be driven without scraping HTML:

- Index: `curl -s https://www.bittensor.com/llms.txt` — every link is raw
  markdown; one page = `https://www.bittensor.com/llms.mdx/docs/<slug>/content.md`.
- Full corpus for grepping (**NOT** for stuffing into context):
  `curl -s https://www.bittensor.com/llms-full.txt | rg -n '<pattern>'`.
- Migration reference:
  `https://www.bittensor.com/llms.mdx/docs/migration/content.md`.
- Chain source search: `https://www.bittensor.com/code/search.json?q=<symbol>`;
  raw file by path via `/code/index.json` → `/code/raw/<repo-path>`.

## Knowing the installed API surface

The authoritative API is the installed package, not memory:

- Version: `python -c "import bittensor; print(bittensor.__version__)"`.
- Surface: `dir(bittensor)`, `help()` / `inspect.signature` on anything you
  call — cross-check against `<venv>/site-packages/bittensor/` source.
- CLI: `btcli --help`, then `-h` per command (command groups, flags and
  shorthands differ between `bittensor-cli` versions).

## General workflow for any Bittensor question

1. Am I 100% certain of every term/definition/unit involved? If not → docs
   (local clone `~/.hermes/cache/subtensor-docs/docs/` first, then `llms.txt` /
   `llms-full.txt` / the specific doc page) BEFORE anything else.
2. Am I 100% certain of the current API/runtime? If not → check the installed
   library source.
3. Only then act: chain queries, testnet dry-runs, or transactions.
This ordering exists because a wrong definition poisons every number derived
from it (see: quoting `locked_mass` in TAO when it is ALPHA — a real error
caught in an SN82 audit, 2026-09).

## btcli for scripts/automation

- `-h` everywhere: group and flag names move between `bittensor-cli` versions;
  never script from memory.
- Reads: machine-readable output via `--json-output` / `--json-out`.
- Automation: always pass `--yes` / `--no-prompt` — a non-interactive session
  (no TTY) without it fails on a confirmation prompt rather than hanging.
- Network selection: `--network` / `--subtensor.network` (name or `ws://`
  endpoint); use a testnet endpoint for anything mutation-shaped during
  testing.
- Wallet options: `--wallet.name` / `--wallet.hotkey` / `--wallet.path`;
  destination options (`--dest`, ...) accept raw ss58, address-book names, or
  local key names (`WALLET/HOTKEY`) — destinations never default.
- Group shorthands (`w`, `st`, `s`, `su`, `c`, `wt`) are first-class command
  names in this CLI line; long forms and shorthands both appear in real repos.
