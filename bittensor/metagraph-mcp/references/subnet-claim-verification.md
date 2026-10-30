# Subnet claim verification (recipes)

Scoped-review toolkit: prove or disprove a subnet's public claims with crypto checks, greps, and chain reads — for when the user asks bounded questions (privacy claims, miner inventory, openness/decentralization rankings) rather than commissioning the full `subnet-im-review` protocol.

## 0. Scope discipline

- Batch site + repo + chain reads into as few turns as possible, verify selectively, then WRITE. The user cuts off open-ended digging mid-run — an answer built from what is already proven beats one more probe.
- Tag every finding VERIFIED / INFERENCE / UNKNOWN, and when proof is demanded, include the check that was actually run (snippet, grep, chain read), never a promise of one.

## 1. Prove the coordinator's signed results (crypto, not trust)

Public, no-auth endpoint pattern: `provider.<x>/api/subnet/v1/epoch/latest` and `/epoch/<n>`.

```python
import hashlib, json, sr25519
from bittensor_wallet import Keypair
d = json.load(open("epoch.raw"))
rj = d["result_json"]            # some endpoints nest the object as d["result"] instead — branch on keys
assert hashlib.sha256(rj.encode()).hexdigest() == d["digest"]   # binding: digest covers the exact served bytes
# The signed preimage format comes from the subnet's own validator sync code; engy SN53 uses:
msg = f"engy-sn53:epoch:v1:{d['netuid']}:{d['epoch_index']}:{d['digest']}".encode()
sig = bytes.fromhex(d["signature"])
pub = Keypair(ss58_address=d["signed_hotkey"]).public_key
assert sr25519.verify(sig, msg, pub)
```

- Deps: `uv venv; uv pip install py-sr25519-bindings bittensor-wallet` (prebuilt wheels, quick).
- Read the subnet's `verify_payload`-style code first: it names the exact preimage string and what is signed (digest of the raw served bytes, never a display field). The repo's validator tests show the expected wire shapes.
- Old wire format (no `result_json`): the signed bytes are the JSON object; reproduce the digest with `json.dumps(result, sort_keys=True, separators=(',', ':'))` and check other canonical forms before alleging tampering.
- Sanity: u16 weight vectors sum to 65535; per-row share = `weight_u16 / 65535`; cross-check top rows against the human epoch leaderboard percentages.
- What this proves / does not: the pinned key signed these exact bytes. Honesty of the contents still needs chain + endpoint cross-checks.

## 2. Public-feed leak check (privacy claims)

- Fetch every public feed of the coordinator (epoch JSONs, miners page, requests page) and grep raw bodies for content keys: `grep -oE '\"[a-z_]*(token|prompt|completion|content|input_ids)[a-z_]*\"' *.raw | sort -u`. Aggregates only (counts, token totals, ppm gates, scores) = the public surface carries no content — say that as evidence about the feed, not about the operator's database.
- Marketing/app site: dump served HTML, grep for tracker vendors (`gtag|posthog|plausible|sentry|segment|clarity|umami`), record present vs absent.
- Read the privacy page for carve-outs and verify each against the product surface: scope qualifiers ("hardware we operate"), per-model exceptions, retained-metadata list. "Zero retention" plus an openly-flagged exception is a disclosure choice, not a lie; a retained field that is content-equivalent (token IDs are detokenizable) does bend the headline — flag it as such.
- Rendering truncates identifiers: dashboards show hotkeys truncated (`5DHAbc…xYz123`) while raw HTML/JSON carries them whole. Save raw bodies AND extracted text; grep the raw for reconciliation.

## 3. Repo audit greps that caught real gaps

- **License**: `ls LICENSE*` + the GitHub API `license` field across the whole org (`/orgs/<org>/repos`). Public without a license is not open source — score openness accordingly.
- **Reproducibility**: for every module/doc named in "reproduce/verify" instructions, grep the repo. Missing commit tools / proof docs = dangling claim; quote the doc line and the absent path.
- **How many miners?** `grep -n "commitment\s*=" miner/*.py` and `grep -n "import toploc" miner/*.py`: proof-attaching miners build real commitments (`build_proofs_base64`); TEE/streaming legs send `{}` and lean on provider-assigned identity.
- **Stale docs vs live bug**: compare `git log --format='%ci %s' -- <doc>` with the file it contradicts — a doc older than the code it disagrees with is stale, not a defect.
- **Tests**: run them in a throwaway venv (`uv venv`, deps, `PYTHONPATH=. pytest tests -q`). Name any module that cannot collect without heavy deps (torch/toploc) — never present a partial green run as full coverage.

## 4. Independence / self-mining cross-check

- Compare the epoch leaderboard's models against the documented "models open to miners": a top-weight hotkey serving models declared first-party-only is evidence of operator self-mining — INFERENCE, never fact.
- Quantify reward concentration: how many keys hold ~99% of the 65,535 weight, and the tail's per-key share. Where a key's ownership is unknown, present both readings and state what would settle it.
- `get_account_identity` on top keys' coldkeys usually returns `has_identity: false` — read that as "unidentifiable", never as "independent".

## 5. Chain probes (metagraph MCP) — what each buys

- `get_subnet_economics` → owner coldkey/hotkey, counts, registration cost, emission share, price.
- `get_subnet_concentration` → Nakamoto per lens (stake vs emission vs validator). Pull 2–3 comparable netuids as baselines before ranking anything.
- `get_subnet_metagraph` sorted by `incentive` with a fields subset → top earners; `axon_earning.earning_miners` vs total = earning vs registered-but-dead.
- `list_subnet_validators` → is the owner/signing key the top validator, and what share of total stake is one entity?
- `get_subnet_weights` → distinct_setters vs weight_sets; a dozen setters all submitting one signed vector is not decentralization.
- `get_tao_usd` for USD conversions (`null` = not priceable, never 0). Provenance: metagraph incentive/emission are the LAST completed tempo; coordinator websites are the operator's own view (claims).

## 6. Report discipline

- Claim tags VERIFIED / INFERENCE / UNKNOWN with the backing check; distrust is the default posture ("a claim is a lie until proven otherwise").
- Ranking asks (openness / decentralization 1–5): named comparisons + the number behind each score + "what would change the score" (license added, verifier open-sourced, setter diversity, model list widened).
- Close by OFFERING the Round-2 adversarial verifier and a saved markdown report — never launch the verifier unprompted.
