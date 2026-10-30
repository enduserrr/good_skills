#!/usr/bin/env python3
"""fetch.py — URL → readable-text fetcher with a least-powerful-first fallback chain.
Usage: ~/scrapers/scrapling/bin/python fetch.py URL [URL...] [--max-chars N] [--out-dir DIR]
Chain per URL: scrapling Fetcher -> StealthyFetcher -> curl -> camoufox JS render (render.py).
Prints a readable excerpt and saves FULL text (with SOURCE_URL header) for citation evidence.
"""
import argparse, hashlib, html as htmllib, pathlib, re, subprocess, time

CAMO_PY = pathlib.Path.home() / "scrapers/camoufox/bin/python"
RENDER = pathlib.Path(__file__).with_name("render.py")


def strip_html(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>|</(p|div|li|tr|h[1-6]|option)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = htmllib.unescape(raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"(\n ?)+", "\n", raw)
    return raw.strip()


def save(url, text, outdir):
    outdir = pathlib.Path(outdir).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[-1])[:70] or hashlib.md5(url.encode()).hexdigest()[:16]
    p = outdir / (stem + ".txt")
    p.write_text("SOURCE_URL: %s\n\n%s" % (url, text), encoding="utf-8")
    return p


def try_scrapling(url, stealth=False):
    try:
        if stealth:
            from scrapling.fetchers import StealthyFetcher as F
        else:
            from scrapling.fetchers import Fetcher as F
        r = F.fetch(url) if stealth else F.get(url)
        status = getattr(r, "status", None)
        try:
            text = r.get_all_text()
        except Exception:
            text = strip_html(getattr(r, "body", "") or "")
        return status, (text or "").strip()
    except Exception as e:
        return None, "FETCH_ERROR: %r" % (e,)


def try_curl(url):
    try:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", "45", "--compressed",
             "-A", "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
             "-H", "Accept: text/html,application/xhtml+xml", url],
            capture_output=True, timeout=60)
        return None, strip_html(out.stdout.decode("utf-8", "replace"))
    except Exception as e:
        return None, "FETCH_ERROR: %r" % (e,)


def try_camo(url):
    try:
        out = subprocess.run([str(CAMO_PY), str(RENDER), url], capture_output=True, timeout=180)
        raw = out.stdout.decode("utf-8", "replace")
        if not raw.strip():
            err = out.stderr.decode("utf-8", "replace")[-300:]
            return None, "FETCH_ERROR: camo empty; stderr: %s" % err
        return None, strip_html(raw)
    except Exception as e:
        return None, "FETCH_ERROR: %r" % (e,)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--max-chars", type=int, default=6000)
    ap.add_argument("--out-dir", default="~/.hermes/cache/fetched-pages")
    a = ap.parse_args()
    for url in a.urls:
        report = ["", "=" * 80, "URL: " + url]
        status, text = try_scrapling(url)
        method = "scrapling"
        if not text or len(text) < 400:
            s2, t2 = try_scrapling(url, stealth=True)
            if t2 and len(t2) > len(text or ""):
                status, text, method = s2, t2, "stealthy"
        if not text or len(text) < 400:
            s2, t2 = try_curl(url)
            if t2 and len(t2) > len(text or ""):
                status, text, method = s2, t2, "curl"
        if (not text or len(text) < 400) and CAMO_PY.exists():
            s2, t2 = try_camo(url)
            if t2 and len(t2) > len(text or ""):
                status, text, method = s2, t2, "camoufox"
        p = save(url, text or "", a.out_dir)
        report.append("STATUS: %s  METHOD: %s  CHARS: %d" % (status, method, len(text or "")))
        report.append("SAVED: %s" % p)
        report.append("-" * 80)
        report.append((text or "")[: a.max_chars])
        print("\n".join(report))
        time.sleep(0.5)


if __name__ == "__main__":
    main()
