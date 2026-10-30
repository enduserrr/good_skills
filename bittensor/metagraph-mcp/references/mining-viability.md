# Assessing mining viability on a Bittensor subnet

Recipe for "can/should I mine subnet X (from this host / at all), what does it cost, could an agent run it autonomously" questions. These tasks are **report-only**: never register a hotkey, install miner software, or open ports unless the user explicitly asks for setup in a later turn.

## 1. Chain state first — `get_subnet_economics(netuid)`

Read the live economics before any project marketing; the chain settles claims the project's site will not.

- **`alpha_in_emission` = 0 with `miner_burned_fraction` = 1** → 100% of miner emission is burned to the owner UID; miners earn exactly nothing no matter what the mechanism docs describe. Check this BEFORE quoting any earning-tier math — a subnet can have a fully implemented, well-documented incentive mechanism that is simply not switched on (SN25/UR operated this way after migrating onto the old Mainframe netuid).
- **`open_slots` = 0** → subnet full (max_uids reached); registering evicts an incumbent and the new registrant gets a short immunity window (~25 h on SN105) before the same can happen to them. Full + high churn = high variance, not a blocker.
- **`registration_cost_tao`** is the real burn, live; it can sit at the floor (fractions of a TAO). Never quote registration cost from blog posts or stale guides — `btcli`/chain shows the real number.
- **`emission_share` is the stage-1 PRICE share** (alpha_price / Σ alpha_price), not TAO earned — never present it as miner income.
- Nominal vs realistic returns: daily alpha emission at spot overstates income because the actual TAO inflow (`SubnetTaoInEmission`) backing the alpha can be ~6× smaller; quote a realistic band. Check pool depth before advising lump unstakes — shallow AMM pools eat slippage.
- **Netuid reuse trap:** subnets change hands (Mainframe → UR on SN25). Any pre-migration source — registries, blog posts, old analyses — describes a different project; check the identity provenance or the analysis's own chain-verification date.

## 2. Sources, in order of trust

1. Chain reads (metagraph MCP / btcli) — settles economics, slots, burn.
2. The subnet's own GitHub repo (chain `github_url` / native_identity) — actual mechanism code, ports, runbook.
3. Project sites often publish **markdown mirrors** — try `<site>/llms.txt` and `<site>/docs-md/<page>.md` before scraping HTML (ur.xyz serves `docs-md/`; the llms.txt convention is spreading).
4. Third-party chain-verified deep dives worth raw-fetching from `raw.githubusercontent.com`:
   - `mikyoch/bittensor-subnet-analyses` — per-subnet source-traced analyses with chain-verification blocks (rules tables, mechanism math).
   - `yuna91/bittensor_maeb_research` — SN105/Beam deployment guide with live-verified costs, scoring constants, penalty tables.
   Always re-check each analysis's verification date against current chain state before reusing its numbers.

## 3. Fetching when web_extract fails

If `web_extract` errors with "search-only backend", fall back to `urllib.request` from `execute_code` with a browser User-Agent (plain Python UA gets 403 on some hosts). SPA pages still carry `<meta name="description">` and JSON-LD with the site's key claims — strip tags and read those rather than giving up on the page.

## 4. Host-fitness check on the local machine

Run `lscpu`, `free -h`, `df -h /`, `ip -brief addr`, and an egress-IP check (`curl https://checkip.amazonaws.com`) — never assume the host profile from memory is current.

Match subnet demands to the host's real constraints:
- **Bandwidth-bound subnets** (data-transfer/VPN/bandwidth) score on routing geography, public-IP reachability, and NAT — a home box behind NAT on a Finnish ISP scores against US-datacenter fleets even with ample CPU/RAM; a ~€15/mo VPS in the right region beats the free home box on every scored axis.
- **IP-inventory subnets** (scored on distinct routable prefixes) need procured IP space; a single residential IP scores near the floor regardless of hardware.
- **Reliability-weighted scoring** (uptime terms in the score) punishes home power/ISP outages directly.
- **Permanent-penalty mechanisms** (one integrity violation zeroing a hotkey forever; sybil `SAME_IP` rules) are autonomy red flags — flag them explicitly when asked whether an agent could run the miner unattended.

## F. Fleet screen — "which subnets are minable from THIS host"

For "find other viable subnets for this machine" asks, screen the whole registry in 3 passes, then verify only survivors:

1. **All-subnets economics in one call** — MCP `get_economics` with `limit: 1000` + `fields` projection (netuid,name,miner_count,open_slots,registration_cost_tao,miner_burned_fraction,alpha_in_emission,emission_share). Pre-rank with `find_subnet_opportunities` boards when a specific axis (cheapest registration / highest emission / open slots) matters.
2. **Hard gates, filter in Python** (never loop MCP per-subnet):
   - `miner_burned_fraction` = 1 (or `alpha_in_emission` = 0) → miners earn $0 today regardless of mechanism docs; drop. This is common (~20% of subnets) and unadvertised.
   - GPU/TEE/archive-scale demands the host can't meet → drop. Registry rows carry `gpu_required` / `min_vram_gb`; REST `/api/v1/subnets?limit=500` returns all rows (incl. `github_languages`) in one fetch — but note `gpu_required` is `None` for many GPU subnets in practice, so don't rely on it alone.
   - Capital/token gates (miners must buy the subnet's token, CMC API keys, etc.) → drop unless the user wants them.
   - `open_slots` = 0 is NOT a gate (most live subnets are full; eviction-churn entry is normal) — report it as variance, not exclusion.
3. **Survivor verification** — for each survivor (aim ≤10), read the chain-registered repo README (REST row `source_repo` → `raw.githubusercontent.com` with browser UA; try `main` then `master`; native-language-repos may 404 both) for real miner hardware specs, then the metagraph economics row for miner count (fewer miners = larger per-miner share of the same emission; a 90-miner subnet at the same emission share beats a 250-miner one). Subnet repos pin specific — often older — SDK versions (10.x while 11 is current): build the miner in its own venv at the repo's pin instead of upgrading the shared environment; the mechanism code targets the pinned API. Prefer subnets offering offline scoring (`--demo`/`--practice`/testnet modes) — they let the user verify the pipeline before paying the burn.

Report: one row per viable subnet (what miners do, host fit, reg cost, miner-reached emission), plus a "not viable despite looking attractive" list WITH the disqualifying reason — the near-misses are the most useful part for the user. Classify autonomy fit: submission-style competitions (agents ARE the work product, validator runs the compute) suit agent operation best; passive-serving subnets need uptime ops; signal/edge subnets automate mechanically but earn nothing without a real edge.

## 5. Report shape

Concise, one block per subnet: how it works (2–3 lines), hardware needs, setup process, setup cost, recurring cost, host verdict, agent-autonomy verdict. End with a comparison table plus a direct "is one clearly more viable" answer. Registration burn live-verified in the table; label income figures nominal vs realistic. State plainly when a subnet pays $0 today.
