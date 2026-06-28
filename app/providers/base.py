"""Provider interface.

A provider knows how to fetch congressional trading data and return it as
lists of plain dicts matching our DB schema. Swap providers via the
FLOORTRADES_PROVIDER env var without touching the rest of the app.
"""
from typing import List, Dict


class Provider:
    name = "base"

    def fetch_filers(self) -> List[Dict]:
        raise NotImplementedError

    def fetch_returns(self) -> List[Dict]:
        raise NotImplementedError

    def fetch_trades(self) -> List[Dict]:
        raise NotImplementedError

    def attribution(self) -> str:
        """Human-readable data-source credit shown in the UI footer."""
        return ""
