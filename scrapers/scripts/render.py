#!/usr/bin/env python3
"""render.py — JS-render a URL with Camoufox (headless) and print page HTML to stdout.
Usage: ~/scrapers/camoufox/bin/python render.py URL
Last-resort tier for scripts/fetch.py when static fetchers return thin/garbage text.
"""
import sys
from camoufox.sync_api import Camoufox

url = sys.argv[1]
with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto(url, timeout=90000, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    print(page.content())
