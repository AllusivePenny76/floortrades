"""Read queries backing the UI. Kept separate from routes for clarity."""
from . import db, config


def leaderboard(chamber=None, party=None, order="weighted_excess", limit=100,
                min_trades=None):
    if min_trades is None:
        min_trades = config.LEADERBOARD_MIN_TRADES
    if order not in ("weighted_excess", "avg_excess", "avg_ret", "scored_buys"):
        order = "weighted_excess"

    where = ["r.scored_buys >= ?"]
    params = [min_trades]
    if chamber in ("house", "senate"):
        where.append("r.chamber = ?")
        params.append(chamber)
    if party in ("D", "R", "I"):
        where.append("r.party = ?")
        params.append(party)

    sql = f"""
        SELECT r.*, f.photo_url, f.office, f.trade_count, f.late_filings
        FROM returns r
        LEFT JOIN filers f ON f.id = r.id
        WHERE {' AND '.join(where)}
        ORDER BY r.{order} DESC
        LIMIT ?
    """
    params.append(limit)
    with db.get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def top_trades(days=None, chamber=None, txn_type=None, late_only=False, limit=50):
    where = ["ticker IS NOT NULL"]
    params = []
    if chamber in ("house", "senate"):
        where.append("chamber = ?")
        params.append(chamber)
    if txn_type == "buy":
        where.append("transaction_type LIKE 'Purchase%'")
    elif txn_type == "sell":
        where.append("transaction_type LIKE 'Sale%'")
    if late_only:
        where.append("is_late = 1")
    if days:
        where.append("transaction_date >= date('now', ?)")
        params.append(f"-{int(days)} days")

    sql = f"""
        SELECT * FROM trades
        WHERE {' AND '.join(where)}
        ORDER BY amount_range_high DESC, transaction_date DESC
        LIMIT ?
    """
    params.append(limit)
    with db.get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def recent_trades(limit=50, **kw):
    """Most recent disclosures by transaction date."""
    where = ["ticker IS NOT NULL"]
    params = []
    if kw.get("chamber") in ("house", "senate"):
        where.append("chamber = ?")
        params.append(kw["chamber"])
    sql = f"""
        SELECT * FROM trades
        WHERE {' AND '.join(where)}
        ORDER BY transaction_date DESC, amount_range_high DESC
        LIMIT ?
    """
    params.append(limit)
    with db.get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def politician(filer_id):
    with db.get_conn() as conn:
        f = conn.execute("SELECT * FROM filers WHERE id=?", (filer_id,)).fetchone()
        r = conn.execute("SELECT * FROM returns WHERE id=?", (filer_id,)).fetchone()
        trades = conn.execute(
            "SELECT * FROM trades WHERE filer_id=? "
            "ORDER BY transaction_date DESC LIMIT 500",
            (filer_id,),
        ).fetchall()
        rank = None
        if r:
            rank = conn.execute(
                "SELECT COUNT(*)+1 AS rank FROM returns "
                "WHERE weighted_excess > (SELECT weighted_excess FROM returns WHERE id=?) "
                "AND scored_buys >= ?",
                (filer_id, config.LEADERBOARD_MIN_TRADES),
            ).fetchone()["rank"]
    return {
        "filer": dict(f) if f else None,
        "returns": dict(r) if r else None,
        "rank": rank,
        "trades": [dict(t) for t in trades],
    }


def ticker(symbol):
    symbol = symbol.upper()
    with db.get_conn() as conn:
        trades = conn.execute(
            "SELECT * FROM trades WHERE ticker=? "
            "ORDER BY transaction_date DESC LIMIT 500",
            (symbol,),
        ).fetchall()
        agg = conn.execute(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN transaction_type LIKE 'Purchase%' THEN 1 ELSE 0 END) AS buys,
                 SUM(CASE WHEN transaction_type LIKE 'Sale%' THEN 1 ELSE 0 END) AS sells,
                 COUNT(DISTINCT filer_id) AS politicians
               FROM trades WHERE ticker=?""",
            (symbol,),
        ).fetchone()
    return {
        "symbol": symbol,
        "agg": dict(agg) if agg else {},
        "trades": [dict(t) for t in trades],
    }


def top_tickers(limit=20, days=90):
    sql = """
        SELECT ticker,
               COUNT(*) AS trades,
               COUNT(DISTINCT filer_id) AS politicians,
               SUM(CASE WHEN transaction_type LIKE 'Purchase%' THEN 1 ELSE 0 END) AS buys,
               SUM(CASE WHEN transaction_type LIKE 'Sale%' THEN 1 ELSE 0 END) AS sells
        FROM trades
        WHERE ticker IS NOT NULL AND transaction_date >= date('now', ?)
        GROUP BY ticker
        ORDER BY trades DESC
        LIMIT ?
    """
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (f"-{int(days)} days", limit)).fetchall()]


def search(q, limit=30):
    like = f"%{q}%"
    with db.get_conn() as conn:
        people = conn.execute(
            "SELECT id, full_name, chamber, party, state, office, photo_url "
            "FROM filers WHERE full_name LIKE ? ORDER BY trade_count DESC LIMIT ?",
            (like, limit),
        ).fetchall()
        tickers = conn.execute(
            "SELECT ticker, COUNT(*) AS trades FROM trades "
            "WHERE ticker LIKE ? GROUP BY ticker ORDER BY trades DESC LIMIT ?",
            (q.upper() + "%", limit),
        ).fetchall()
    return {
        "people": [dict(p) for p in people],
        "tickers": [dict(t) for t in tickers],
    }


def overview_stats():
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM trades) AS trades,
                 (SELECT COUNT(*) FROM filers) AS filers,
                 (SELECT COUNT(*) FROM trades WHERE is_late=1) AS late,
                 (SELECT MAX(transaction_date) FROM trades) AS latest"""
        ).fetchone()
    return dict(row) if row else {}
