---
name: scrapers
version: 2.1.0
description: "Use when scraping: scrapling/camoufox/ungoogled-chromium stack — usage, install, quirks."
license: MIT
author: ais (enduserrr) + NoSleepHermes
metadata:
  hermes:
    tags: [scraping, scrapling, camoufox, ungoogled-chromium, setup]
---

# Scrapers

Scraping stack: usage, install, and hard-won quirks in one place. All user-local, no sudo.

## Standing rules

- **Build venvs with `uv`, never `python3 -m venv`.** uv works identically on Linux, macOS and Windows, and on minimal Linux boxes without ensurepip/python3-venv plain venv creation half-succeeds and breaks pip.
- Dedicated venv per tool under `<tools>/<tool>/`, never the Hermes env.
- **Prefer no stock Chromium/Chrome.** If a Chromium-codebase browser is truly needed, ungoogled-chromium is the only acceptable choice, and only on explicit user request. Prefer Camoufox (Gecko) for stealth work.
- Verify an install with a real command (`python -m camoufox version`, a live `Fetcher.get`) before reporting success; browser-launch smoke tests may need user approval — prepare the script and hand it over rather than blocking.

## Layout

Paths below use the POSIX form (`<tools>/...`, `<venv>/bin/python`). On Windows the equivalents are `%USERPROFILE%\scrapers\...` and `<venv>\Scripts\python.exe`; commands are otherwise identical (PowerShell or cmd).

| Layer | Path | Engine | Use |
|---|---|---|---|
| HTTP fetch + parsing | `<tools>/scrapling` (venv, scrapling 0.4.x) | httpx/curl_cffi | static pages, APIs, adaptive selectors; **no browser** (browser fetchers skipped on install) |
| Stealth browser | `<tools>/camoufox` (venv, camoufox 0.5.6) | Gecko (Firefox fork, C++-patched) | anti-bot walls, JS pages; browser binary in the user cache dir (~1.2 GB) |
| Ungoogled Chromium | platform install (see its section) | Chromium de-Googled | only on explicit request; wired to scrapling browser fetchers via `SCRAPLING_EXECUTABLE_PATH` |

Run scripts with the owning venv's python: `<tools>/scrapling/bin/python`, `<tools>/camoufox/bin/python`.

## Requirements & install (any platform)

Three components, least-powerful first — scrapling and camoufox are required for the skill to function at all; ungoogled-chromium is optional and only on explicit user request. Nothing needs admin rights.

**0. Install uv** (one-time, user-local):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

**1. scrapling** — HTTP fetching/parsing (httpx/curl_cffi), no browser binaries:

```bash
uv venv <tools>/scrapling
uv pip install --python <tools>/scrapling/bin/python "scrapling[fetchers]"
```
On systems with a working ensurepip you may additionally run `<tools>/scrapling/bin/python -m scrapling install` to pull browser binaries for DynamicFetcher — skip it on minimal boxes (that's why browser fetchers were skipped here).

**2. camoufox** — stealth Gecko browser:

```bash
uv venv <tools>/camoufox
uv pip install --python <tools>/camoufox/bin/python camoufox
<tools>/camoufox/bin/python -m camoufox fetch   # ~1.2GB → user cache dir (~/.cache/camoufox; %LOCALAPPDATA%\camoufox on Windows)
```

**3. ungoogled-chromium** — optional; see its section below.

Verify before use: `python -m camoufox version` and one live `Fetcher.get('https://example.com')`.

## Scrapling usage

### Fetchers (choose least-powerful that works)
```python
from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher
```
| Fetcher | Use | Notes |
|---|---|---|
| `Fetcher` (or `AsyncFetcher`) | static HTML, APIs | httpx-based, fast, no browser |
| `StealthyFetcher` | Cloudflare/anti-bot walls | curl_cffi browser impersonation |
| `DynamicFetcher` | JS-rendered pages | real browser (patchright/playwright) |

Common kwargs: `headless=True`, `network_idle=True`, `adaptive=True`, `proxy=...`, `geoip=True` (Stealthy: match proxy's geo).

```python
page = StealthyFetcher.fetch('https://example.com', headless=True, network_idle=True)
```

**scrapling 0.4.x API quirks**: `Fetcher.get(url)` but `StealthyFetcher.fetch(url)` — the two classes differ. Calling `.get()` on `StealthyFetcher` raises `AttributeError: type object 'StealthyFetcher' has no attribute 'get'`, which kills that fallback tier silently; if a blocked page returns nothing, check this first. Response has `.css`, `.xpath`, `.body`, `.get_all_text` — NOT `.css_first`. Browsers in 0.4.x are Chromium-based; no Camoufox fetcher in this version.

### Parsing / adaptive selection
```python
page.css('.product', auto_save=True)      # first run: store selector signature
page.css('.product', adaptive=True)       # later: auto-relocates after site redesign
page.css_first('h1::text'), page.xpath('//a/@href'), page.find(text='Price')
```
Full selector docs: https://scrapling.readthedocs.io/en/latest/parsing/selection.html

### Spiders (multi-page crawls)
```python
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "demo"
    start_urls = ["https://example.com/"]

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {"title": item.css_first('h2::text')}
```
Run: `<tools>/scrapling/bin/python -m scrapling spiders run demo` (check `scrapling --help` / CLI docs).
Features: concurrent, pause/resume, auto proxy rotation, adaptive crawl speed + backoff.

### CLI / MCP
- CLI: `scrapling fetch <url>`, `scrapling spiders ...` — https://scrapling.readthedocs.io/en/latest/cli/overview.html
- MCP server extra: `pip install "scrapling[ai]"`, docs: /en/latest/ai/mcp-server.html

## Camoufox (stealth browser, Firefox/Gecko fork)

No sudo needed for install or updates.

Usage (Playwright API over Juggler):
```python
from camoufox.sync_api import Camoufox          # async: camoufox.async_api
with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
```

- **geoip extra** (`camoufox[geoip]`): lets `geoip=True` match timezone/locale/coords to the exit IP. Only matters with VPN/proxy (mismatched IP↔clock is a standard detection tell); identical without one. If the host runs no VPN/proxy, plain install is correct; add the geoip extra when one exists.
- CLI (`<tools>/camoufox/bin/python -m camoufox <cmd>`): `path`, `version` (banner w/ sizes), `fetch` (idempotent), `list`/`set <ver>`/`active`, `remove [--select]`, `server` (Playwright server). Check `version` for actual installed state instead of assuming versions.
- Update: `uv pip install --python <tools>/camoufox/bin/python -U camoufox` then `python -m camoufox fetch`.

## ungoogled-chromium (only on explicit user request)

Official prebuilt binaries come from the ungoogled-software/ungoogled-chromium-binaries repo — pick your platform's directory (`linux_portable`, `windows`, `macos`, ...); there is no auto-updater on any platform, re-download to upgrade.

**Linux** (no apt/PPA — portable tarball):
1. Read `<version>.ini` under `config/platforms/linux_portable/64bit/` for the newest version + sha256.
2. `curl -LO <url>`; verify sha256; `tar -x` to /opt.
3. `sudo` (user runs it): `mkdir -p /opt/ungoogled-chromium && tar -xf <tarball> -C /opt/ungoogled-chromium --strip-components=1`, symlink `chrome` to `/usr/local/bin/ungoogled-chromium`.

**Windows**: grab the installer or 7z archive from the repo's `windows` directory; the installer handles PATH, the archive just needs unzipping to a fixed folder (point `SCRAPLING_EXECUTABLE_PATH` at `chrome.exe`).

Wire into Scrapling: `executable_path='<chrome-path>'` per call, or set `SCRAPLING_EXECUTABLE_PATH` (user env; env fallback lives at scrapling/engines/_browsers/_base.py:576; also what Scrapling's MCP reads).

Linux only — missing system libs after tarball install (`libatk-1.0.so.0` etc.): `sudo <tools>/camoufox/bin/python -m playwright install-deps chromium` installs the full dep set. Careful: under sudo `~` expands to root's home — always use absolute paths to the venv binaries. Windows/macOS need no extra runtime libs.

## Hermes web_extract backend

Default backend (ddgs) is search-only — URL extraction fails until an extract backend is configured. Tavily works keyless (no account, rate-limited): `hermes config set web.extract_backend tavily`. SearXNG is search-only; pair it with an extract provider. Requires Hermes restart to apply.

## URL→text fetch helper (`scripts/fetch.py`)

When you need readable page text and `web_extract` can't extract, run the canned helper instead of hand-rolling fetch code:

```bash
<tools>/scrapling/bin/python <this-skill-dir>/scripts/fetch.py <url> [<url>...] [--max-chars 6000] [--out-dir DIR]
```

- Fallback chain, least-powerful first: scrapling `Fetcher` → `StealthyFetcher` → `curl` → camoufox JS render (`scripts/render.py`, headless, slow last resort); a tier is skipped upward when the text comes back under ~400 chars.
- Saves FULL text of every page to `--out-dir` (default `~/.hermes/cache/fetched-pages/`) with a `SOURCE_URL:` header — that saved file is exactly what downstream citation/quoting tools need; register and quote directly from it.
- Politeness sleep between URLs is built in; keep batches small.
- Paths derive from `Path.home()` — when hand-typing Hermes cache paths, the root is `~/.hermes/cache`, not `~/cache`, or downstream tools read the wrong (empty) directory.

## Safety rules

- Public pages only; respect robots.txt; rate-limit; check site ToS before authed scraping.
- Stealthy/Dynamic fetchers ARE anti-detection tools — user bears legal/ToS responsibility; don't enable on targets the user hasn't approved.
- Test in the venv; never install into Hermes's own environment.

## Docs

- Official: scrapling.readthedocs.io, camoufox.com, ungoogled-software.github.io/ungoogled-chromium-binaries
