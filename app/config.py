"""Application configuration, sourced from environment variables.

All settings have sensible defaults so the app runs with zero configuration,
which is a requirement for the Umbrel app store.
"""
import os

# Where the SQLite database lives. On Umbrel this is mounted to persistent storage.
DATA_DIR = os.environ.get("FLOORTRADES_DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "floortrades.db")

# Which ingestion provider to use. Pluggable so the app is not hostage to a
# single upstream feed. See app/providers/.
PROVIDER = os.environ.get("FLOORTRADES_PROVIDER", "kadoa")

# How often to refresh data, in hours. Disclosures update at most daily.
REFRESH_HOURS = int(os.environ.get("FLOORTRADES_REFRESH_HOURS", "24"))

# Pull fresh data on startup if the DB is empty or stale.
REFRESH_ON_START = os.environ.get("FLOORTRADES_REFRESH_ON_START", "true").lower() == "true"

# Minimum scored buys required for a politician to appear on the leaderboard.
# Filters out filers with too little history to rank meaningfully.
LEADERBOARD_MIN_TRADES = int(os.environ.get("FLOORTRADES_LEADERBOARD_MIN_TRADES", "5"))

# Optional API key for providers that require one (e.g. FMP, Finnhub).
PROVIDER_API_KEY = os.environ.get("FLOORTRADES_PROVIDER_API_KEY", "")

# Pull deep historical trades (e.g. the 2012-2020 Senate archive) and merge
# them onto the matching politician. Accumulates over time.
BACKFILL_ENABLED = os.environ.get("FLOORTRADES_BACKFILL", "true").lower() == "true"

APP_NAME = "FloorTrades"
APP_VERSION = "1.1.0"
