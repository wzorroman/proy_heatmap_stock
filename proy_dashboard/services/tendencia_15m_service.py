"""services/tendencia_15m_service.py — Tendencias en Marcha (K2): K1 ∩ ADX.

Panel K2: mismo universo que K1 (extremos de banda de Bollinger + volumen)
intersectado con `ADX 15m ≥ umbral`. Es el **filtro de régimen** de K1: de los
extremos que K1 marca, K2 muestra los que además tienen tendencia fuerte.

Visual: `z_bandexis (X) × ADX 15m (Y)` — comparte eje X con K1 (σ). Mismos
símbolos que K1, con la dimensión ADX añadida.
"""

from __future__ import annotations

from core.settings import Settings
from services.bar_15m_service import _f, _r4


class Tendencia15mService:
    def __init__(self, bollinger_service, latest_tick_repo, settings: Settings) -> None:
        self.bollinger_service = bollinger_service
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("tendencia", default={})

    def _adx_min(self) -> float:
        return float(self._cfg().get("adx_min", 25))

    def _max(self) -> int:
        # Mismo límite que K1 (bollinger_scatter_max) para garantizar los mismos símbolos.
        return int(self.settings.business("trading_15m", "bollinger_scatter_max", default=10))

    def scan(self) -> list[dict]:
        """Universo K1 (Bollinger 20, σ) intersectado con ADX 15m ≥ umbral."""
        bollinger_filas = self.bollinger_service.scan(limit=self._max())
        ticks = {
            r["symbol"]: r
            for r in self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        }
        adx_min = self._adx_min()
        filas = []
        for b in bollinger_filas:
            t = ticks.get(b["symbol"])
            if not t:
                continue
            adx = _f(t.get("adx_15"))
            if adx is None or adx < adx_min:
                continue
            filas.append({**b, "adx_15": _r4(adx)})
        return filas