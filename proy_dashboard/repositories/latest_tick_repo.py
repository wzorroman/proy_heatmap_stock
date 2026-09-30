"""repositories/latest_tick_repo.py — último tick por activo."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from repositories.base import BaseRepository

_SELECT = """
SELECT l.asset_id, a.symbol, a.asset_class, a.logical_key, a.is_canonical, a.role,
       a.sector, l.timestamp_utc, l.close, l.change_pct, l.volume, l.rsi,
       l.rsi_15, l.cci20_15, l.bbpower_15, l.adx_15, l.pivot_r3_15,
       l.update_mode, l.feed_delay_s
FROM latest_market_tick l
JOIN dim_asset a USING (asset_id)
"""


class LatestTickRepository(BaseRepository):
    def fetch_all(self, asset_classes: Optional[Sequence[str]] = None) -> list[dict]:
        sql = _SELECT
        params = None
        if asset_classes:
            sql += " WHERE a.asset_class = ANY(%s)"
            params = (list(asset_classes),)
        return self.fetch(sql + " ORDER BY a.symbol", params)

    def fetch_by_logical_keys(self, logical_keys: Sequence[str]) -> list[dict]:
        return self.fetch(
            _SELECT + " WHERE a.logical_key = ANY(%s) ORDER BY a.is_canonical DESC",
            (list(logical_keys),),
        )

    def max_timestamp(self) -> Optional[datetime]:
        row = self.fetch_one("SELECT max(timestamp_utc) AS ts FROM latest_market_tick")
        return row["ts"] if row else None
