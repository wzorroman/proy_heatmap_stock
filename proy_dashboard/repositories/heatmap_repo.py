"""repositories/heatmap_repo.py — snapshots del heatmap (treemap/sectorial)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from repositories.base import BaseRepository

_LATEST = "(SELECT max(timestamp_utc) FROM fact_heatmap_snapshot)"

_SELECT = """
SELECT h.asset_id, a.symbol, a.ticker, a.company_name, a.sector,
       h.timestamp_utc, h.price_heatmap, h.daily_change_pct, h.market_cap,
       h.volume, h.avg_vol_10d, h.avg_vol_30d, h.volatility_d, h.change_abs,
       h.high_52w, h.low_52w
FROM fact_heatmap_snapshot h
JOIN dim_asset a USING (asset_id)
WHERE h.timestamp_utc = {latest}
""".format(latest=_LATEST)


class HeatmapRepository(BaseRepository):
    def fetch_latest(
        self, limit: Optional[int] = None, asset_classes: Optional[list[str]] = None
    ) -> list[dict]:
        sql = _SELECT
        params: list = []
        if asset_classes:
            sql += " AND a.asset_class = ANY(%s)"
            params.append(list(asset_classes))
        sql += " ORDER BY h.market_cap DESC NULLS LAST"
        if limit:
            sql += " LIMIT %s"
            params.append(int(limit))
        return self.fetch(sql, tuple(params) if params else None)

    def vol_map(self) -> dict[int, float]:
        rows = self.fetch(
            "SELECT asset_id, avg_vol_10d FROM fact_heatmap_snapshot "
            "WHERE timestamp_utc = " + _LATEST
        )
        return {r["asset_id"]: r["avg_vol_10d"] for r in rows if r.get("avg_vol_10d")}

    def sectores(self, min_activos: int = 5) -> list[dict]:
        return self.fetch(
            f"""
            SELECT a.sector,
                   count(*)                    AS n_activos,
                   avg(h.daily_change_pct)     AS change_medio,
                   sum(h.market_cap)           AS market_cap_total,
                   count(*) FILTER (WHERE h.daily_change_pct > 0) AS ganadores,
                   count(*) FILTER (WHERE h.daily_change_pct < 0) AS perdedores,
                   avg((h.volume / NULLIF(h.avg_vol_10d, 0) - 1) * 100) AS vol_medio
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a USING (asset_id)
            WHERE h.timestamp_utc = {_LATEST}
            GROUP BY a.sector
            HAVING count(*) >= %s
            ORDER BY change_medio DESC NULLS LAST
            """,
            (int(min_activos),),
        )

    def rotacion(self, ventanas: int = 12) -> list[dict]:
        return self.fetch(
            """
            SELECT timestamp_utc,
                   count(*)                  AS n_activos,
                   avg(daily_change_pct)     AS change_medio
            FROM fact_heatmap_snapshot
            WHERE timestamp_utc IN (
                SELECT DISTINCT timestamp_utc FROM fact_heatmap_snapshot
                ORDER BY timestamp_utc DESC LIMIT %s
            )
            GROUP BY timestamp_utc
            ORDER BY timestamp_utc
            """,
            (int(ventanas),),
        )

    def max_timestamp(self) -> Optional[datetime]:
        row = self.fetch_one("SELECT max(timestamp_utc) AS ts FROM fact_heatmap_snapshot")
        return row["ts"] if row else None

    def distribucion_change(self, limit: int = 1000) -> list[float]:
        rows = self.fetch(
            f"SELECT daily_change_pct FROM fact_heatmap_snapshot "
            f"WHERE timestamp_utc = {_LATEST} AND daily_change_pct IS NOT NULL "
            f"ORDER BY market_cap DESC NULLS LAST LIMIT %s",
            (int(limit),),
        )
        return [float(r["daily_change_pct"]) for r in rows]

    def fetch_sectores(self, min_activos: int = 1) -> list[dict]:
        return self.fetch(
            f"""
            SELECT a.sector AS sector, count(*) AS n
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a USING (asset_id)
            WHERE h.timestamp_utc = {_LATEST}
            GROUP BY a.sector
            HAVING count(*) >= %s
            ORDER BY n DESC NULLS LAST
            """,
            (int(min_activos),),
        )

    def fetch_por_sector(
        self, sector: str, asset_classes: Optional[list[str]] = None, limit: int = 60
    ) -> list[dict]:
        clases = list(asset_classes) if asset_classes else ["equity"]
        return self.fetch(
            f"""
            SELECT a.symbol, a.company_name, a.sector,
                   h.price_heatmap, h.daily_change_pct, h.market_cap,
                   h.volume, h.avg_vol_10d, h.high_52w, h.low_52w, h.volatility_d,
                   l.rsi, l.adx_15
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a USING (asset_id)
            LEFT JOIN latest_market_tick l USING (asset_id)
            WHERE h.timestamp_utc = {_LATEST}
              AND a.asset_class = ANY(%s)
              AND a.sector = %s
            ORDER BY h.market_cap DESC NULLS LAST
            LIMIT %s
            """,
            (clases, sector, int(limit)),
        )

    def buscar_stocks(
        self, q: str, asset_classes: Optional[list[str]] = None, limit: int = 60
    ) -> list[dict]:
        clases = list(asset_classes) if asset_classes else ["equity"]
        patron = f"%{q}%"
        return self.fetch(
            f"""
            SELECT a.symbol, a.company_name, a.sector,
                   h.price_heatmap, h.daily_change_pct, h.market_cap,
                   h.volume, h.avg_vol_10d, h.high_52w, h.low_52w, h.volatility_d,
                   l.rsi, l.adx_15
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a USING (asset_id)
            LEFT JOIN latest_market_tick l USING (asset_id)
            WHERE h.timestamp_utc = {_LATEST}
              AND a.asset_class = ANY(%s)
              AND (a.symbol ILIKE %s OR a.ticker ILIKE %s OR a.company_name ILIKE %s)
            ORDER BY h.market_cap DESC NULLS LAST
            LIMIT %s
            """,
            (clases, patron, patron, patron, int(limit)),
        )

    def top_equity_rsi(
        self,
        limit: int = 25,
        asset_classes: Optional[list[str]] = None,
        rsi_alto: Optional[float] = None,
        rsi_bajo: Optional[float] = None,
    ) -> list[dict]:
        """Acciones (equity/common) de mayor capitalización con su RSI del último tick.

        Si `rsi_alto`/`rsi_bajo` se indican, filtra solo las que están en zona de
        oportunidad (RSI ≥ alto o RSI ≤ bajo).
        """
        clases = list(asset_classes) if asset_classes else ["equity"]
        sql = f"""
            SELECT a.symbol, a.company_name, a.sector,
                   h.market_cap, h.daily_change_pct, l.rsi
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a USING (asset_id)
            JOIN latest_market_tick l USING (asset_id)
            WHERE h.timestamp_utc = {_LATEST}
              AND a.asset_class = ANY(%s)
              AND h.market_cap IS NOT NULL
              AND l.rsi IS NOT NULL
        """
        params: list = [clases]
        if rsi_alto is not None and rsi_bajo is not None:
            sql += " AND (l.rsi >= %s OR l.rsi <= %s)"
            params.extend([float(rsi_alto), float(rsi_bajo)])
        sql += " ORDER BY h.market_cap DESC LIMIT %s"
        params.append(int(limit))
        return self.fetch(sql, tuple(params))
