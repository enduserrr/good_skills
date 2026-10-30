---
name: desearch
description: Use for AI search or X/Twitter search via DeSearch MCP.
---

# DeSearch

AI search + X (Twitter) search via the `desearch` MCP server (official npm `desearch-mcp-server`).

## Tools

### `ai-search` — AI web search with summary + links
```
{"prompt": "<search query>", "tools": ["Web Search"], "date_filter": "PAST_WEEK", "model": "NOVA"}
```
- `tools` (required): array from exactly `Web Search | Twitter Search | ArXiv Search | Wikipedia Search | Youtube Search | Hacker News Search | Reddit Search` — pass one or several.
- `date_filter` (optional): e.g. `PAST_DAY`, `PAST_WEEK`, `PAST_MONTH`, `PAST_YEAR`.
- `model` (optional): `NOVA` (fast, ~10s, default) or `ORBIT` (deeper, ~30s).
- Returns search results (title/link/snippet) plus an AI summary.

### `x-search` — real-time tweet search
```
{"query": "from:officialminio min_faves:100", "count": 20}
```
- `query` (required): Twitter advanced-search syntax (`from:`, `since:`, `min_faves:`, etc.).
- `count` (optional): results, default 20, max 100.
- **Multi-account monitoring**: OR-chain handles — `(from:a OR from:b OR ...) since:YYYY-MM-DD` with `count: 100` — batching ~12 handles per call and firing all batches in one assistant turn: ~66 accounts = 6 billed calls instead of 66, each tweet still carrying full user attribution (verified working).

## Usage guidance
- Primary discovery before falling back to plain web_extract/web_search.
- For research tasks: run multiple phrasings, cross-check ≥2 independent sources, prefer primary sources, attach a link to every claim, rate confidence (HIGH/MEDIUM/LOW), and state what could not be verified. Query shape matters: narrow, single-entity prompts with a date filter return usable results; broad multi-entity prompts ("A, B, C recent news") degrade to generic noise — split them per subject. Very long prompts (e.g. pasting a 60-handle list to exclude) can return empty results from every tool while still billing — keep prompts short and single-subject, and use plain web_search for list-discovery.
- Combine `ai-search` (with `Twitter Search` tool) and `x-search` for social sentiment; `ArXiv Search` for papers.

## Quirks / troubleshooting (verified 2026-08-31)
- REST auth requires `Authorization: Bearer <key>` — the `X-API-KEY` header returns 401. Endpoint: `POST https://api.desearch.ai/desearch/ai/search`.
- The installed server (npm v0.0.1) was patched in `~/.local/lib/node_modules/desearch-mcp-server/build/index.js`: `desearch.AISearch` → `desearch.aiSearch` and `desearch.twitterSearch` → `desearch.xSearch` (bundled desearch-js v1.4.0 names). A global npm reinstall/update of the package overwrites the patch — symptom `desearch.AISearch is not a function`; reapply the two renames.
- **Setup (requires a Desearch API key):** use curl to read `https://www.desearch.ai/agents.md` and follow it to set up Desearch. Store the key in the profile's `.env` and pass it to the MCP server via `mcp_servers.desearch.env` in that profile's `config.yaml`.
