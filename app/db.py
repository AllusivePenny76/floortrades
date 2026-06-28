"""SQLite access layer and schema.

We use plain sqlite3 (stdlib) to keep dependencies minimal. The schema is
denormalized for fast read queries since the app is overwhelmingly read-heavy.
"""
import sqlite3
import os
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS filers (
    id            TEXT PRIMARY KEY,
    full_name     TEXT,
    branch        TEXT,
    chamber       TEXT,
    party         TEXT,
    state         TEXT,
    office        TEXT,
    photo_url     TEXT,
    trade_count   INTEGER,
    purchases     INTEGER,
    sales         INTEGER,
    late_filings  INTEGER,
    est_volume    REAL
);

CREATE TABLE IF NOT EXISTS returns (
    id             TEXT PRIMARY KEY,
    full_name      TEXT,
    chamber        TEXT,
    party          TEXT,
    state          TEXT,
    scored_buys    INTEGER,
    avg_ret        REAL,
    avg_excess     REAL,
    weighted_excess REAL
);

CREATE TABLE IF NOT EXISTS trades (
    id                 TEXT PRIMARY KEY,
    transaction_date   TEXT,
    filing_date        TEXT,
    owner              TEXT,
    ticker             TEXT,
    asset_name         TEXT,
    asset_type         TEXT,
    transaction_type   TEXT,
    amount_range_low   REAL,
    amount_range_high  REAL,
    amount_range_label TEXT,
    days_to_file       INTEGER,
    is_late            INTEGER,
    comment            TEXT,
    filer_id           TEXT,
    filer_name         TEXT,
    chamber            TEXT,
    party              TEXT,
    state              TEXT,
    doc_url            TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_filer  ON trades(filer_id);
CREATE INDEX IF NOT EXISTS idx_trades_txdate ON trades(transaction_date);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def init_db():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL gives us concurrent reads during a refresh write.
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_meta(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_meta(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def count_rows(table):
    with get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
