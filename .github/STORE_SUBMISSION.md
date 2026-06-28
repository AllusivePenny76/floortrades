# Add FloorTrades — congressional stock-trading tracker

FloorTrades is a self-hosted tracker for U.S. congressional stock trading. It
collects public STOCK Act disclosures and presents them as a leaderboard
(politicians auto-ranked by estimated excess return), a trade-flow view (biggest
& most-recent trades, late filings flagged), per-politician pages, per-ticker
pages, and search.

## Checklist

- [x] **Open source** — MIT licensed
- [x] **Self-hosted** — no mandatory external account; all data stored locally in SQLite
- [x] **Multi-arch** — image built for `linux/amd64` and `linux/arm64`
- [x] **No config-file editing required** — runs with zero configuration
- [x] **Reverse proxied** via `app_proxy`
- [x] **Persistent data** under `${APP_DATA_DIR}/data`
- [x] **Healthcheck** endpoint (`/healthz`)
- [ ] Gallery screenshots (`gallery/1.jpg`, `2.jpg`, `3.jpg`)

## Data & privacy

Data comes from public financial-disclosure systems (U.S. House Clerk, Senate
eFD, OGE) via open datasets; no third-party account or API key is required. The
app makes only outbound HTTPS requests to refresh public data. Disclosures are
self-reported in dollar ranges, so all figures are clearly labeled as estimates,
and the UI states it is not investment advice.

## Source

https://github.com/YOUR_GITHUB_USERNAME/floortrades
