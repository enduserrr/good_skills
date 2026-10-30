# Multi-subnet overview report recipe

Task shape: user asks for a dense overview of N named subnets (e.g. "compelle sn84, cacheon sn14, gittensor sn74") covering value proposition, what miners do, how miners are ranked, current stage, and open-sourceness. Deliverable: a markdown report note (header line, `### tags` section, one dense block per subnet + compare table).

## Data per subnet
1. **Numbers**: `get_subnet_economics` (include_summary false) — miner/validator counts, alpha price + 1d/7d/1m change, alpha mcap/FDV, volume, registration cost, miner_burned_fraction, first_emission_block / registered_at_block (age + prior occupants).
2. **Mechanism**: official docs and repo README, not third-party explainer sites. When the web_extract backend is search-only, `curl -sL raw.githubusercontent.com/<org>/<repo>/main/README.md` (try `master` too) and the docs' `llms.txt` give clean text. Chain identity (`SubnetIdentitiesV3` via get_subnet_detail) names the official repo — treat that as the repo to read.
3. **Stage**: README "Status" sections + first_emission_block recency + price trend. A subnet mid mechanism-migration or pre-open on mainnet is "watchlist", and the report should say so.
4. **Open-sourceness assessment** (judgment, label it as such): official repo exists? license? public docs? verifiable unauthenticated API/dashboard? independent analyses? Grade: good / partial / closed, with one-line evidence. Distinguish "docs open" from "interface verifiable" (docs can advertise an API whose OpenAPI spec is an empty file).

## Report structure
Per subnet: `## SNxx — Name (domain)` with bolded one-paragraph sections (Value proposition / What miners do / How miners are ranked / Stage / Open-sourceness), then a **Quick compare** markdown table (domain, miners, alpha price, 30d, mcap, stage, opensourceness). Dense > long: no filler prose, numbers inline.

## Ranking-mechanism vocabulary worth using
WTA/winner-takes-most, incumbent-relative baselines (score = beating the reigning kernel, not stock), commit-reveal + submission cost, decaying crown vs confiscation, king-of-the-hill broad-win gates, burned share for non-qualifying miners, owner-run single validator (centralization caveat).
