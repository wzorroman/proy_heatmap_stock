"""repositories/indicator_repo.py — indicadores multi-TF (formato largo)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from repositories.base import BaseRepository


class IndicatorTfRepository(BaseRepository):
    def fetch_recent(
        self, tf: str, limit: int = 3000, asset_classes: Optional[list[str]] = None
    ) -> list[dict]:
        sql = """
            SELECT i.asset_id, a.symbol, a.asset_class, i.timestamp_utc, i.tf,
                   i.rsi, i.cci20, i.bbpower, i.adx,
                   i.change_pct, i.volume, i.pivot_r3
            FROM fact_market_indicator_tf i
            JOIN dim_asset a USING (asset_id)
            WHERE i.tf = %s
        """
        params: list = [tf]
        if asset_classes:
            sql += " AND a.asset_class = ANY(%s)"
            params.append(list(asset_classes))
        sql += " ORDER BY i.timestamp_utc DESC LIMIT %s"
        params.append(int(limit))
        return self.fetch(sql, tuple(params))

    def fetch_by_asset(self, asset_id: int, tf: str, limit: int = 5) -> list[dict]:
        return self.fetch(
            """
            SELECT asset_id, timestamp_utc, tf, rsi, cci20, bbpower, adx, change_pct
            FROM fact_market_indicator_tf
            WHERE asset_id = %s AND tf = %s
            ORDER BY timestamp_utc DESC LIMIT %s
            """,
            (asset_id, tf, int(limit)),
        )

    def max_timestamp(self, tf: Optional[str] = None) -> Optional[datetime]:
        if tf:
            row = self.fetch_one(
                "SELECT max(timestamp_utc) AS ts FROM fact_market_indicator_tf WHERE tf = %s",
                (tf,),
            )
        else:
            row = self.fetch_one("SELECT max(timestamp_utc) AS ts FROM fact_market_indicator_tf")
        return row["ts"] if row else None
