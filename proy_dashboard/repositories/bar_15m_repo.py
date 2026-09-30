"""repositories/bar_15m_repo.py — barras de 15 min y fallback a ticks."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from repositories.base import BaseRepository


class Bar15mRepository(BaseRepository):
    """Lectura de barras 15m y de ticks subyacentes para ensamblar barras."""

    def fetch_barras(
        self, symbol: str, since: datetime, limit: int = 500
    ) -> list[dict]:
        """Barras OHLC 15m ya materializadas en `fact_market_bar_15m`."""
        return self.fetch(
            """
            SELECT b.asset_id, a.symbol, b.bar_start_utc AS timestamp_utc,
                   b.open, b.high, b.low, b.close,
                   b.volume_delta AS volume, b.n_ticks, b.is_regular,
                   b.session_date
            FROM fact_market_bar_15m b
            JOIN dim_asset a USING (asset_id)
            WHERE a.symbol = %s AND b.bar_start_utc >= %s
            ORDER BY b.bar_start_utc
            LIMIT %s
            """,
            (symbol, since, int(limit)),
        )

    def fetch_ticks(
        self, symbol: str, since: datetime, limit: int = 5000
    ) -> list[dict]:
        """Ticks crudos de `fact_market_series` para ensamblar barras 15m."""
        return self.fetch(
            """
            SELECT s.timestamp_utc, s.close, s.volume
            FROM fact_market_series s
            JOIN dim_asset a USING (asset_id)
            WHERE a.symbol = %s AND s.timestamp_utc >= %s
            ORDER BY s.timestamp_utc
            LIMIT %s
            """,
            (symbol, since, int(limit)),
        )

    def fetch_latest_per_symbol(
        self, symbols: list[str], since: datetime
    ) -> list[dict]:
        """Última barra 15m para cada símbolo solicitado."""
        if not symbols:
            return []
        return self.fetch(
            """
            SELECT DISTINCT ON (a.symbol)
                   b.asset_id, a.symbol, b.bar_start_utc AS timestamp_utc,
                   b.open, b.high, b.low, b.close,
                   b.volume_delta AS volume, b.n_ticks, b.is_regular
            FROM fact_market_bar_15m b
            JOIN dim_asset a USING (asset_id)
            WHERE a.symbol = ANY(%s) AND b.bar_start_utc >= %s
            ORDER BY a.symbol, b.bar_start_utc DESC
            """,
            (list(symbols), since),
        )

    def max_bar_timestamp(self) -> Optional[datetime]:
        row = self.fetch_one("SELECT max(bar_start_utc) AS ts FROM fact_market_bar_15m")
        return row["ts"] if row else None

    def fetch_equity_symbols(self, limit: int = 500) -> list[str]:
        """Símbolos equity que tienen barras 15m recientes."""
        return [
            r["symbol"]
            for r in self.fetch(
                """
                SELECT DISTINCT a.symbol
                FROM fact_market_bar_15m b
                JOIN dim_asset a USING (asset_id)
                WHERE a.asset_class = 'equity'
                ORDER BY a.symbol
                LIMIT %s
                """,
                (int(limit),),
            )
        ]
