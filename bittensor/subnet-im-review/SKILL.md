---
name: subnet-im-review
version: 1.0.0
author: ais (enduserrr) + NoSleepHermes
license: MIT
description: Use when deep-auditing any Bittensor subnet adversarially.
tags: [bittensor, subnet, incentive-mechanism, adversarial-review, metagraph]
---

# Subnet Incentive-Mechanism Review (`subnet-im-review`)
*NEVER trust a subnet, subnet owner, subnet team or other affiliate. A claim is a lie until proven otherwise!*
Two-round protocol for deep subnet audits: **(1)** initial research → draft report; **(2)** a detached adversarial verifier session (default GLM-5.3, reasoning MAX — honor any user override for model/effort) that spawns its own subagents to disprove, debunk, and expose every flaw in the draft; **(3)** rebuild the final report only from what survives. Scope: subnet codebase, incentive mechanism, chain data, owner wallets.

## Non-negotiable principles (from the original prompt — carry into every round and every child prompt)

1. **NEVER trust a subnet, its owner, or any affiliate.** Marketing sites, READMEs, gists, docs, and dashboards are CLAIMS by an interested party — evidence of what they say, not of what is true. "Don't trust, verify — sometimes more than once."
2. **The worst possible failure is hallucinating or guessing.** An honest "inconclusive", "unverifiable", or "I don't know" is always acceptable and always preferred over a plausible invention. Flag inference vs. fact explicitly.
3. **Code claims must be verifiable facts**: every statement about a repo must carry a file path, function name, or quoted snippet a reader can check. NEVER claim what the code does — report what it demonstrably does, traceable and able to stand under ridicule.
4. **Distinguish LIVE code from DEAD code**: grep for call sites before describing a mechanism as active (e.g. SN82's epsilon weight budget existed in source but was never called).
5. **Verify term definitions against Bittensor docs** before doing arithmetic on chain values — units betray you (`locked_mass` is denominated in ALPHA, not TAO; alpha vs TAO vs rao). Docs: `curl -s https://www.bittensor.com/llms-full.txt | rg -n '<term>'`, per-page markdown at `https://www.bittensor.com/llms.mdx/docs/<slug>/content.md`.
6. **A final report is issued ONLY after the draft has been put to test, broken down, and rebuilt.** No exceptions.

## Round 1 — Initial research (in-session)

Load the `bittensor` skill first for SDK/docs conventions. Workstreams (parallelize with delegate_task where the streams are independent):

**A. Codebase** (clone to /tmp, shallow OK):
- How is miner input read (extrinsic/storage, size limits, gist pointers)? What does the validator actually run, with which models/providers, who pays?
- Where does configuration live — repo, or owner-controlled remote (gists, endpoints)? How often pulled, fail-open or fail-closed? What can the owner change without a code release?
- Scoring/weight-setting: exact algorithm, constants, thresholds. Quote the weight-set code path.
- Telemetry: what is POSTed where, default on/off, real opt-out vs documented opt-out.
- Anti-gaming machinery (its existence = evidence that gaming happens).
- **Miner requirements to start mining**: exact hardware (GPU/VRAM/CPU/RAM/disk), software deps, model weights/API keys (and who pays for them), registration cost, ongoing burn/commitment — from the repo's actual code and run scripts, NOT the README's promises.
- What a reader might MISS: kill switches, burn-mirrors, auto-updaters, misleading deploy docs.

**B. Website + public APIs** (curl; save HTML under an audit dir):
- Static numbers in HTML are often STALE FALLBACKS overwritten by JS from an API — fetch `/api/stats`-style endpoints and reconcile before claiming any "inconsistency".
- Test downloads without auth (HTTP status codes), public per-item APIs, manifest/sha256 verification schemes, robots.txt.
- Quote exact text for every claim; record fetch timestamps (UTC).

**C. Chain data** (metagraph MCP; use field projections + sort/limit, never dump 256-row snapshots):
- Economics: `get_subnet_economics` (alpha price, market cap, emission share, miner/validator counts, registration).
- Incentive concentration: `get_subnet_concentration` + `get_subnet_metagraph` with `min_incentive`/`sort_by` — how many neurons actually earn? Winner-take-all?
- Validator control: per-validator stake/coldkeys — owner share vs. others, Nakamoto coefficient.
- **Owner wallet tracing** (the round most reviews skip): owner coldkey/hotkey from economics; `get_account_transfers`, `get_account_counterparties` for flow between owner and the largest holders/nominators; conviction locks via `get_subnet_conviction` (convert ALPHA→TAO at spot before quoting TAO equivalents). Distinguish verified flows from "likely the same entity" (label it as inference).
- Remember metagraph epoch provenance: incentive/emission reflect the LAST completed tempo, not live activity.

**D. Draft report** (format below), explicitly marking every claim VERIFIED / PARTIALLY / REFUTED / UNVERIFIABLE / INFERENCE with its source.

## Round 2 — Adversarial verification (detached session)

Launch a separate background Hermes session whose ONLY job is to break the draft. Default: **GLM-5.3 Flash, reasoning MAX** — honor any user override for model/effort.

1. Write the draft + protocol to a query file:
```bash
mkdir -p ~/.hermes/reviews/subnet-reviews/<netuid>
# write draft to ~/.hermes/reviews/subnet-reviews/<netuid>/draft.md and the verifier prompt to verify-prompt.md (see below)
```
2. Launch detached (tmux gives it a TTY — a piped/non-TTY run silently degrades to oneshot and kills its delegated children):
```bash
tmux new-session -d -s sn<netuid>-verify "hermes chat --yolo --accept-hooks --reasoning max -m <model> --provider <provider> --query-file ~/.hermes/reviews/subnet-reviews/<netuid>/verify-prompt.md -s subnet-im-review"
tmux pipe-pane -t sn<netuid>-verify -o 'cat >> ~/.hermes/reviews/subnet-reviews/<netuid>/verify-session.log'
```
3. Poll the log (`tail`) until the session reports completion; the verifier writes `verdicts.md` next to the draft.

**Verifier prompt template** (the session must be able to spawn its own subagents via delegate_task for parallel repo/website/chain re-audits):
- Role: adversarial verifier. Mission: disprove, debunk, and surface every flaw, error, omission, and unsupported leap in the attached draft report. Same rigor as the draft demanded of its sources.
- For EVERY claim in the draft: independently re-verify against primary sources (clone the repo, curl the site/APIs, query the chain). Verdict VERIFIED / PARTIALLY VERIFIED / REFUTED / UNVERIFIABLE, with quoted evidence and paths.
- Specifically hunt: (a) hallucinated specifics — wrong constants, wrong file names, wrong numbers; (b) dead-code-vs-live-path confusion; (c) stale-HTML vs live-API confusion; (d) unit/definition errors on chain values; (e) owner/affiliate narratives taken at face value; (f) material omissions cutting EITHER way; (g) conclusions that outrun their evidence; (h) equipment/requirements stated from READMEs or marketing instead of the repo's actual code and run scripts.
- Write verdicts to `~/.hermes/reviews/subnet-reviews/<netuid>/verdicts.md`; end with an overall assessment of which draft conclusions survive.

## Round 3 — Final report (only after Round 2)

Rebuild the draft incorporating every verdict: correct the refuted, caveat the unverifiable, keep the verified with sources. **Output discipline: FOCUSED, RELEVANT, CONCISE.** The report exists to answer three reader questions — what the subnet provides (value proposition), what miners do at a low level, and what it takes to start mining. Every section must serve one of those; cut anything that doesn't. Output format (modeled on the SN82 Compelle report):

1. **Value proposition** — what the subnet actually provides, to whom, and whether the market pays for it (revenue/volume evidence, not marketing claims).
2. **What miners do (low level)** — mechanism in prose, constants inline, chain-verified state: the actual workload, step by step, from task fetch to submission to scoring.
3. **Requirements to mine** — hardware (GPU/VRAM/CPU/RAM), software, models/API keys (who pays), registration + ongoing costs, and estimated break-even vs. incentive distribution. Everything traceable to code, not README promises.
4. **What it creates / value table** — artifact | status (with live evidence) | value.
5. **Points FOR the subnet** — bulleted, each with source.
6. **Points AGAINST the subnet** — bulleted, each with source.
7. **Versus the naive/private alternative** — what, if anything, is non-replicable.
8. **Final conclusion** — MORE CONCISE than the SN82 report's: a few sentences integrating verified economics, incentive structure, and owner-flow facts. State plainly what is verified vs. inferred vs. unknown. If the honest answer is "inconclusive on X", say exactly that.

Sign as `NoSleepHermes` when stored/published. Offer to save the final report as a markdown note (`<netuid>-<slug>-report.md`) wherever the user keeps reports.

## Pitfalls (hard-won, SN82 session)
- "Internal inconsistency" between site pages is usually stale static fallback vs live API — check JS before alleging contradiction.
- "Commercially licensed corpus" may still be 95% free (per-item APIs, verdict-only downloads) — test actual access, don't read the pricing page's framing.
- Emission concentration numbers differ by lens: miner-incentive holders vs emission holders vs stake Nakamoto — state which lens each number uses.
- Alpha-denominated values (conviction locks, market caps) need explicit price conversion; check the chain-doc definition of every field first.
- Owner dominance can hide behind nominators: trace transfer flows between owner coldkey and top stakers before calling a validator "independent" — and label entity-attribution as inference unless flows prove it.
- Metagraph `get_subnet_detail` with `sections` can fail schema validation; use `get_subnet_economics` / `get_subnet` instead.
- Neuron `stake_tao` on dTAO subnets is alpha-denominated despite the field name — cross-check any per-neuron stake claim against the subnet's `alpha_market_cap_tao` before quoting TAO (SN105 draft error, caught only in Round 2).
- Marketing "hero stats" may be client-side random-walk animations, not stale API data — grep the site's JS bundles for `setInterval`/`Math.random` around the number before alleging staleness or inconsistency (SN105: 847 Gb/s was fabricated in-browser).
