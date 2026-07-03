"""Pull data from the active provider into SQLite.

filers & returns are full snapshots from the provider, so they are replaced
wholesale each run. trades are *accumulated*: we upsert by id and never delete,
so the provider's rolling recent-window builds an ever-growing local history,
and historical backfill sources can merge in deep history.
"""
import logging
import datetime as dt

from . import db, config, backfill
from .providers import get_provider

log = logging.getLogger("floortrades.ingest")

_FILER_COLS = [
    "id", "full_name", "branch", "chamber", "party", "state", "office",
    "photo_url", "trade_count", "purchases", "sales", "late_filings", "est_volume",
]
_RETURN_COLS = [
    "id", "full_name", "chamber", "party", "state", "scored_buys",
    "avg_ret", "avg_excess", "weighted_excess",
]
_TRADE_COLS = [
    "id", "transaction_date", "filing_date", "owner", "ticker", "asset_name",
    "asset_type", "transaction_type", "amount_range_low", "amount_range_high",
    "amount_range_label", "days_to_file", "is_late", "comment", "filer_id",
    "filer_name", "chamber", "party", "state", "doc_url",
]


def _replace(conn, table, cols, rows):
    placeholders = ", ".join(["?"] * len(cols))
    collist = ", ".join(cols)
    conn.execute(f"DELETE FROM {table}")
    conn.executemany(
        f"INSERT INTO {table} ({collist}) VALUES ({placeholders})",
        [tuple(r.get(c) for c in cols) for r in rows],
    )


def _upsert_trades(conn, rows):
    placeholders = ", ".join(["?"] * len(_TRADE_COLS))
    collist = ", ".join(_TRADE_COLS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _TRADE_COLS if c != "id")
    conn.executemany(
        f"INSERT INTO trades ({collist}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}",
        [tuple(r.get(c) for c in _TRADE_COLS) for r in rows],
    )


def _name_to_filer(filers):
    """normalized full_name -> {id, chamber, party, state} for backfill name matching."""
    out = {}
    for f in filers:
        key = backfill._norm_name(f.get("full_name"))
        if key:
            out[key] = {"id": f["id"], "chamber": f.get("chamber"),
                        "party": f.get("party"), "state": f.get("state")}
    return out


def refresh(force=False):
    """Fetch and load all data. Returns a summary dict."""
    provider = get_provider()
    log.info("Refreshing data via provider '%s'", provider.name)

    filers = provider.fetch_filers()
    returns = provider.fetch_returns()
    trades = provider.fetch_trades()

    with db.get_conn() as conn:
        _replace(conn, "filers", _FILER_COLS, filers)
        _replace(conn, "returns", _RETURN_COLS, returns)
        _upsert_trades(conn, trades)

    summary = {"filers": len(filers), "returns": len(returns), "primary_trades": len(trades)}

    # Historical backfill (accumulates; safe to re-run thanks to stable ids).
    if config.BACKFILL_ENABLED:
        name_map = _name_to_filer(filers)
        for name, fn in backfill.SOURCES.items():
            try:
                hist = fn(name_map)
                with db.get_conn() as conn:
                    _upsert_trades(conn, hist)
                summary[f"backfill_{name}"] = len(hist)
            except Exception:
                log.exception("Backfill source '%s' failed (continuing)", name)

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    db.set_meta("last_refresh", now)
    db.set_meta("provider", provider.name)
    db.set_meta("attribution", provider.attribution())
    summary["total_trades"] = db.count_rows("trades")
    summary["last_refresh"] = now
    log.info("Refresh complete: %s", summary)
    return summary


def needs_refresh(max_age_hours):
    if db.count_rows("trades") == 0:
        return True
    last = db.get_meta("last_refresh")
    if not last:
        return True
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except ValueError:
        return True
    age = dt.datetime.now(dt.timezone.utc) - last_dt
    return age > dt.timedelta(hours=max_age_hours)
