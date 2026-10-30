# 🦜 Good Skills - a drop in package

Curated skills for a Hermes agent (or some other). Each top-level dir is a skill
you can copy into Hermes's `skills/` directory.

*(`bittensor/` is a category folder holding three related skills so copy it whole.)*

## Contents

| Directory | Skill | Needs |
|---|---|---|
| `test-driven-development/` | TDD discipline (RED-GREEN-REFACTOR) | nothing |
| `plan/` | Markdown implementation plans in `.hermes/plans/` | nothing |
| `bittensor/` | Bittensor SDK/CLI work (`bittensor`, `metagraph-mcp`, `subnet-im-review`); targets SDK v10, one migration reference | see setup |
| `desearch/` | AI search + X/Twitter search via MCP | **API key** |
| `scrapers/` | scrapling/camoufox/ungoogled-chromium scraping stack | venvs on target host |
| `development-safety/` | Never impact live systems; develop on copies | nothing |
| `concise-output/` | Default compressed-output register | nothing |
| `project-continuity/` | QUESTBOOK.md session-logging protocol | nothing |
| `time/` | Agent stopwatch for time-boxing | nothing (stdlib only) |

## Setup notes

- **desearch** — requires a Desearch API key. Setup: `curl -s https://www.desearch.ai/agents.md`
  and follow it. Key goes in the profile's `.env`, wired via `mcp_servers.desearch.env`.
- **bittensor/metagraph-mcp** — uses the metagraph MCP server (`https://api.metagraph.sh/mcp`);
  add it under `mcp_servers` in the target instance's config.
- **bittensor** — optional local docs cache: run `bittensor/scripts/update-bt-docs.sh`
  (cron it, e.g. twice daily) to keep `~/.hermes/cache/subtensor-docs/docs/` fresh;
  the skill falls back to live web docs without it.
- **scrapers** — expects per-tool venvs under `~/scrapers/<tool>/` built with `uv`
  (install commands are in the skill). Scripts `fetch.py`/`render.py` ship inside the skill.
- **subnet-im-review** — Round-2 verifier launches a detached `hermes chat` session;
  fill in your own `-m <model> --provider <provider>`.

## Notes

- `plan/` references subagent/delegation tooling generically — pair with whatever
  delegation skill the target instance has.
- `development-safety` lists `context-compression` / `systematic-debugging` /
  `test-driven-development` as related skills; only the last ships here.
