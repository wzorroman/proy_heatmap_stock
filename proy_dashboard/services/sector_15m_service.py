"""services/sector_15m_service.py — cambio medio 15m por sector.

Agrupa las acciones del screener por sector (según `latest_market_tick`) y
calcula el cambio % medio de la última barra 15m de cada sector.
"""

from __future__ import annotations

from collections import defaultdict

from core.settings import Settings
from services.bar_15m_service import _r4


class Sector15mService:
    def __init__(self, screener_15m_service, latest_tick_repo, settings: Settings) -> None:
        self.screener_15m_service = screener_15m_service
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def por_sector(self) -> list[dict]:
        """Cambio medio 15m por sector, ordenado de mayor a menor."""
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        sector_map = {
            r["symbol"]: (r.get("sector") or "—") for r in rows if r.get("symbol")
        }
        filas = self.screener_15m_service.scan()
        return self.agregar(sector_map, filas)

    # ── cálculo puro (testeable sin BD) ──────────────────────────────────────
    @staticmethod
    def agregar(sector_map: dict, filas: list[dict]) -> list[dict]:
        agg: dict[str, list[float]] = defaultdict(list)
        for f in filas:
            cambio = f.get("change_pct")
            if cambio is None:
                continue
            agg[sector_map.get(f["symbol"], "—")].append(float(cambio))

        salida = [
            {
                "sector": sector,
                "change_pct": _r4(sum(v) / len(v)),
                "n": len(v),
            }
            for sector, v in agg.items()
            if v
        ]
        salida.sort(key=lambda s: -s["change_pct"])
        return salida
