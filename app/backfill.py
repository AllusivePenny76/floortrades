"""Historical backfill sources.

The primary provider exposes only a rolling window of recent trades. These
backfill sources seed deep history that would otherwise take years to
accumulate. They are normalized into the same trade schema and merged onto the
correct politician (by name) when that politician also exists in the primary
feed, so old and new trades share one page.

Senate: the Senate Stock Watcher archive covers 2012-2020 and is the same data
filed on efdsearch.senate.gov. (House lacks an equivalent free structured feed;
its full history exists only as individual PDF filings.)
"""
import re
import hashlib
import logging
from typing import List, Dict, Callable

import httpx

log = logging.getLogger("floortrades.backfill")

SENATE_ARCHIVE_URL = (
    "https://raw.githubusercontent.com/timothycarambat/"
    "senate-stock-watcher-data/master/aggregate/all_transactions.json"
)

TIMEOUT = httpx.Timeout(60.0)

_MONEY_RE = re.compile(r"\$\s*([\d,]+)")


def _parse_amount(s):
    """'$1,001 - $15,000' -> (1001.0, 15000.0); 'Over $50,000,000' -> (5e7, None)."""
    if not s:
        return None, None
    nums = [float(n.replace(",", "")) for n in _MONEY_RE.findall(s)]
    if not nums:
        return None, None
    low = nums[0]
    high = nums[1] if len(nums) > 1 else None
    return low, high


def _to_iso(d):
    """'11/10/2020' -> '2020-11-10'. Returns None if unparseable."""
    if not d:
        return None
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", d)
    if not m:
        return None
    mm, dd, yyyy = m.groups()
    return f"{yyyy}-{int(mm):02d}-{int(dd):02d}"


def _norm_name(n):
    """Loose normalization for matching names across feeds."""
    if not n:
        return ""
    n = n.lower()
    n = re.sub(r"[.,]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _slug(n):
    return re.sub(r"[^a-z0-9]+", "_", _norm_name(n)).strip("_")


def _clean(s):
    return " ".join(s.split()) if s else s


def _get_json(url):
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


def senate_archive_trades(name_to_filer: Dict[str, Dict]) -> List[Dict]:
    """Fetch & normalize the Senate archive into our trade schema.

    name_to_filer maps normalized full_name -> {id, party, state} from the
    primary feed, so historical trades attach to the same politician page.
    """
    rows = _get_json(SENATE_ARCHIVE_URL)
    out = []
    for r in rows:
        senator = r.get("senator")
        if not senator:
            continue
        iso = _to_iso(r.get("transaction_date"))
        low, high = _parse_amount(r.get("amount"))
        ticker = (r.get("ticker") or "").strip().upper()
        if ticker in ("", "--", "N/A"):
            ticker = None

        match = name_to_filer.get(_norm_name(senator))
        filer_id = match["id"] if match else f"ssw_senate_{_slug(senator)}"
        party = match.get("party") if match else None
        state = match.get("state") if match else None

        # Stable synthetic id so re-runs upsert instead of duplicating.
        raw = f"ssw|{senator}|{r.get('transaction_date')}|{ticker}|{r.get('type')}|{r.get('amount')}|{r.get('owner')}"
        tid = "ssw_" + hashlib.sha1(raw.encode()).hexdigest()[:20]

        out.append({
            "id": tid,
            "transaction_date": iso,
            "filing_date": None,
            "owner": r.get("owner"),
            "ticker": ticker,
            "asset_name": _clean(r.get("asset_description")),
            "asset_type": r.get("asset_type"),
            "transaction_type": r.get("type"),
            "amount_range_low": low,
            "amount_range_high": high,
            "amount_range_label": r.get("amount"),
            "days_to_file": None,
            "is_late": 0,
            "comment": r.get("comment"),
            "filer_id": filer_id,
            "filer_name": senator,
            "chamber": "senate",
            "party": party,
            "state": state,
            "doc_url": r.get("ptr_link"),
        })
    log.info("Senate archive: %d historical trades normalized", len(out))
    return out


# Registry of backfill sources: name -> callable(name_to_filer) -> [trades]
SOURCES: Dict[str, Callable] = {
    "senate_archive": senate_archive_trades,
}
