"""Default provider: the MIT-licensed congress-trading-monitor open dataset.

It publishes precomputed static JSON (trades, per-filer returns, filer
profiles) refreshed from the official House Clerk, Senate eFD, and OGE
disclosure sources. No API key required.

Source: https://github.com/kadoa-org/congress-trading-monitor (MIT)
"""
from typing import List, Dict
import httpx

from .base import Provider

BASE = "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data"

TIMEOUT = httpx.Timeout(60.0)


def _get_json(name: str):
    url = f"{BASE}/{name}"
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _f(v):
    """Coerce to float or None."""
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


class KadoaProvider(Provider):
    name = "kadoa"

    def fetch_filers(self) -> List[Dict]:
        rows = _get_json("filers.json")
        return [
            {
                "id": r.get("id"),
                "full_name": r.get("full_name"),
                "branch": r.get("branch"),
                "chamber": r.get("chamber"),
                "party": r.get("party"),
                "state": r.get("state"),
                "office": r.get("office"),
                "photo_url": r.get("photo_url"),
                "trade_count": _i(r.get("trade_count")),
                "purchases": _i(r.get("purchases")),
                "sales": _i(r.get("sales")),
                "late_filings": _i(r.get("late_filings")),
                "est_volume": _f(r.get("est_volume")),
            }
            for r in rows
            if r.get("id")
        ]

    def fetch_returns(self) -> List[Dict]:
        rows = _get_json("returns.json")
        return [
            {
                "id": r.get("id"),
                "full_name": r.get("full_name"),
                "chamber": r.get("chamber"),
                "party": r.get("party"),
                "state": r.get("state"),
                "scored_buys": _i(r.get("scored_buys")),
                "avg_ret": _f(r.get("avg_ret")),
                "avg_excess": _f(r.get("avg_excess")),
                "weighted_excess": _f(r.get("weighted_excess")),
            }
            for r in rows
            if r.get("id")
        ]

    def fetch_trades(self) -> List[Dict]:
        rows = _get_json("trades.json")
        out = []
        for r in rows:
            if not r.get("id"):
                continue
            out.append(
                {
                    "id": r.get("id"),
                    "transaction_date": r.get("transaction_date"),
                    "filing_date": r.get("filing_date"),
                    "owner": r.get("owner"),
                    "ticker": (r.get("ticker") or "").strip().upper() or None,
                    "asset_name": _clean(r.get("asset_name")),
                    "asset_type": r.get("asset_type"),
                    "transaction_type": r.get("transaction_type"),
                    "amount_range_low": _f(r.get("amount_range_low")),
                    "amount_range_high": _f(r.get("amount_range_high")),
                    "amount_range_label": r.get("amount_range_label"),
                    "days_to_file": _i(r.get("days_to_file")),
                    "is_late": _i(r.get("is_late")) or 0,
                    "comment": r.get("comment"),
                    "filer_id": r.get("filer_id"),
                    "filer_name": r.get("filer_name"),
                    "chamber": r.get("chamber"),
                    "party": r.get("party"),
                    "state": r.get("state"),
                    "doc_url": r.get("doc_url"),
                }
            )
        return out

    def attribution(self) -> str:
        return (
            "Data: congress-trading-monitor (MIT), aggregated from U.S. House "
            "Clerk, Senate eFD & OGE disclosures."
        )


def _clean(s):
    """Asset names in the feed sometimes carry runs of whitespace/newlines."""
    if not s:
        return s
    return " ".join(s.split())
