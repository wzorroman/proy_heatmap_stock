"""repositories/series_repo.py — series técnicas (historia y backfill)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from repositories.base import BaseRepository


class SeriesRepository(BaseRepository):
    def fetch_serie(self, symbol: str, since: datetime, limit: int = 2000) -> list[dict]:
        return self.fetch(
            """
            SELECT s.timestamp_utc, s.close, s.volume, s.rsi, s.cci20, s.bbpower,
                   s.adx, s.perf_w, s.change_pct
            FROM fact_market_series s
            JOIN dim_asset a USING (asset_id)
            WHERE a.symbol = %s AND s.timestamp_utc >= %s
            ORDER BY s.timestamp_utc
            LIMIT %s
            """,
            (symbol, since, int(limit)),
        )

    def fetch_desde(self, since: datetime, asset_classes: Optional[list[str]] = None,
                    limit: int = 200000) -> list[dict]:
        """Filas para backfill: incluye asset_id/asset_class para agrupar por ciclo."""
        sql = """
            SELECT s.asset_id, a.symbol, a.asset_class, s.timestamp_utc,
                   s.close, s.volume, s.rsi, s.cci20, s.bbpower, s.adx, s.change_pct
            FROM fact_market_series s
            JOIN dim_asset a USING (asset_id)
            WHERE s.timestamp_utc >= %s
        """
        params: list = [since]
        if asset_classes:
            sql += " AND a.asset_class = ANY(%s)"
            params.append(list(asset_classes))
        sql += " ORDER BY s.timestamp_utc LIMIT %s"
        params.append(int(limit))
        return self.fetch(sql, tuple(params))

    def distinct_timestamps(self, since: datetime) -> list[datetime]:
        rows = self.fetch(
            "SELECT DISTINCT timestamp_utc FROM fact_market_series "
            "WHERE timestamp_utc >= %s ORDER BY timestamp_utc",
            (since,),
        )
        return [r["timestamp_utc"] for r in rows]
