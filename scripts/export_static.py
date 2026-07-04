"""Export the app as a static site (e.g. for GitHub Pages).

Renders every page through the real FastAPI app against the current SQLite
data, then rewrites the HTML for static hosting:
  - drops interactive-only chrome (search box, refresh button, filter forms;
    the Biggest/Most-recent tabs survive as real exported pages)
  - rewrites root-absolute URLs under BASE_PATH (project pages live at
    https://<user>.github.io/<repo>/, not the domain root)
  - injects Open Graph / Twitter meta so shared links unfurl nicely

Usage:
  FLOORTRADES_DATA_DIR=... PYTHONPATH=<deps> python3 scripts/export_static.py <outdir>
Env:
  BASE_PATH  URL prefix of the site (default "/floortrades")
  SITE_URL   absolute site URL for OG tags
             (default "https://allusivepenny76.github.io/floortrades")
"""
import os
import re
import sys
import shutil
import sqlite3
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = os.environ.get("BASE_PATH", "/floortrades").rstrip("/")
SITE = os.environ.get("SITE_URL", "https://allusivepenny76.github.io/floortrades").rstrip("/")
OUT = sys.argv[1] if len(sys.argv) > 1 else "site"

OG_DESCRIPTION = (
    "See how U.S. politicians trade stocks — every STOCK Act disclosure, "
    "ranked by estimated returns. Free & open source."
)

SAFE_TICKER = re.compile(r"^[A-Za-z0-9.\-]+$")

# form-stripping patterns (non-greedy, dotall)
RE_SEARCH_FORM = re.compile(r'<form class="search".*?</form>', re.S)
RE_REFRESH_FORM = re.compile(r'<form action="/refresh".*?</form>', re.S)
RE_FILTER_FORM = re.compile(r'<form class="filters".*?</form>', re.S)
RE_TABS = re.compile(r'(<div class="tabs">.*?</div>)', re.S)

REPO_LINK = '<a class="link-btn" href="https://github.com/allusivepenny76/floortrades">Self-host this app →</a>'


def transform(html: str, path: str) -> str:
    html = RE_SEARCH_FORM.sub("", html)
    html = RE_REFRESH_FORM.sub(REPO_LINK, html)

    # filter forms: keep the tabs (they're plain links), drop the selects
    def _filters(m):
        tabs = RE_TABS.search(m.group(0))
        return tabs.group(1) if tabs else ""
    html = RE_FILTER_FORM.sub(_filters, html)

    # tab links -> exported static variants, then generic BASE prefixing
    html = html.replace('href="/trades?view=top"', f'href="{BASE}/trades/top/"')
    html = html.replace('href="/trades?view=recent"', f'href="{BASE}/trades/recent/"')
    html = re.sub(r'(href|src|action)="/', rf'\1="{BASE}/', html)

    og = (
        f'<meta property="og:site_name" content="FloorTrades">\n'
        f'<meta property="og:title" content="FloorTrades — how politicians trade stocks">\n'
        f'<meta property="og:description" content="{OG_DESCRIPTION}">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:url" content="{SITE}{path}">\n'
        f'<meta property="og:image" content="{SITE}/static/og.png">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="description" content="{OG_DESCRIPTION}">\n'
    )
    return html.replace("</head>", og + "</head>")


def write(path_parts, html):
    p = os.path.join(OUT, *path_parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(html)


def main():
    os.environ.setdefault("FLOORTRADES_REFRESH_ON_START", "false")
    from fastapi.testclient import TestClient
    from app import config
    from app.main import app

    conn = sqlite3.connect(os.path.join(config.DATA_DIR, "floortrades.db"))
    politicians = [r[0] for r in conn.execute(
        "SELECT id FROM filers UNION SELECT DISTINCT filer_id FROM trades WHERE filer_id IS NOT NULL")]
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM trades WHERE ticker IS NOT NULL") if SAFE_TICKER.match(r[0])]
    conn.close()

    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree("app/static", os.path.join(OUT, "static"))
    open(os.path.join(OUT, ".nojekyll"), "w").close()

    pages = skipped = 0
    with TestClient(app) as client:
        def export(url, parts, og_path):
            nonlocal pages, skipped
            r = client.get(url)
            if r.status_code != 200:
                skipped += 1
                return
            write(parts, transform(r.text, og_path))
            pages += 1

        export("/", ["index.html"], "/")
        export("/trades?view=top", ["trades", "top", "index.html"], "/trades/top/")
        export("/trades?view=recent", ["trades", "recent", "index.html"], "/trades/recent/")
        export("/trades?view=top", ["trades", "index.html"], "/trades/")
        for pid in politicians:
            export(f"/politician/{urllib.parse.quote(pid)}",
                   ["politician", pid, "index.html"], f"/politician/{pid}/")
        for sym in tickers:
            export(f"/ticker/{urllib.parse.quote(sym)}",
                   ["ticker", sym, "index.html"], f"/ticker/{sym}/")

        # 404 page (GitHub Pages serves 404.html for unknown paths)
        r = client.get("/politician/__does_not_exist__")
        write(["404.html"], transform(r.text, "/404"))

    print(f"exported {pages} pages to {OUT}/ ({skipped} skipped)")


if __name__ == "__main__":
    main()
