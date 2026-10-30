# Subnet screening sweeps (feature-vs-standalone typing)

Recipe for judging MANY subnets in one pass (typing/screening) — the lightweight counterpart to the `subnet-im-review` Round 1-3 deep audit. Output is instinct-based claims for the user to attack; never launch the adversarial verifier unprompted (see the protocol-routing rule in SKILL.md).

## Recipe

1. Enumerate: metagraph MCP `list_subnets` (limit 100, paginate `cursor`, check `total`). Skip netuid 0.
2. Bulk-fetch profiles from the REST mirror on the MCP host (e.g. `https://api.metagraph.sh`), browser User-Agent header on every request:
   - `GET /api/v1/subnets/{netuid}/profile` → description at `data.profile.native_identity.description`, plus `derived_description`, `categories`, verified surfaces.
   - `GET /api/v1/search?q=<name>` → curated one-liner when the chain description is empty.
   - Loop in `execute_code`, write JSONL to the workspace, aggregate/count in Python; verify the row count against the registry `total`.
3. Backfill empty descriptions (~15% of chain identities) from `derived_description`, `categories`, and verified-surface names before declaring anything unclassifiable.
4. Triage verdicts: strong feature / borderline / standalone-commodity-or-infra / extractor / excluded (dead, parked, no info). Report counts plus honest caveats: a description-based verdict is a claim to be attacked, not an audit finding — label it as such.
5. Spot-verify with web search only the handful of ambiguous subnets that materially change the final list; everything else stays description-based and labeled.

## Feature test (Dropbox test)

A working, even valuable, service can still be a FEATURE. Ask:
1. Could a large platform/AI vendor ship it as a checkbox inside an existing suite?
2. Does anything require Bittensor specifically, or flow back to it — or does the subnet only consume emissions?
3. Is the problem costly enough that open competitive mining beats a centralized incumbent long-term?

Failing these ⇒ feature. A subnet whose (sole) owner only consumes emissions ⇒ extractor bucket.

## Category instincts (starting points; re-derive each sweep)

- Feature-prone: detection/moderation (AI-text, deepfakes), compression/optimization pipeline steps, AutoML, lead-gen, tagging, single-domain analytics, gateway/router wrappers, "X as a commodity" modes chat vendors already ship natively (deep research).
- Not features (infra/commodity/platform): compute marketplaces, verified-inference infra, data commodities (scrapes, conversation corpora), search engines, security-research markets, DeFi products (lending, stablecoins, DEX aggregation), storage/cloud, exchanges/liquidity, robotics/sim platforms, model factories/routers, multi-challenge research platforms.
- Ambiguous by design: long-context, weather, time-series foundation models, forecasting, RAG plumbing, AI companions, voice/utterance engines, synthetic data (identity/genome) — apply the feature test; mark borderline when defensible either way.

## Pitfalls

- On-chain identity fields are operator-controlled: names like "pending...", "deprecated", "Parked", "for sale" appear on chain — identify the subnet from curated metadata, not the native name.
- Metagraph MCP `sections` projections strip server-required keys → schema-validation error on `get_subnet` AND `get_subnet_detail`; call without `sections` and project locally.
- REST `/subnets` pagination is `limit` only (up to 500 returns the full registry in one response); `offset`/`page` params return 400 and there is no cursor — don't probe pagination params, just raise `limit`.
- Skepticism outranks benefit-of-the-doubt: the burden is on a subnet to prove it is a standalone, not on the reviewer to prove it is not.
