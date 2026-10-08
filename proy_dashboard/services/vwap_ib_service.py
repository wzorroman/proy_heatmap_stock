"""services/vwap_ib_service.py — VWAP + Initial Balance: continuación de ruptura.

Panel 2.5 (J2). Para cada acción combina dos estructuras intradía:

  - **IB**: ruptura del rango inicial 09:30–10:00 NY (`InitialBalanceService`).
  - **VWAP**: lado del VWAP acumulado (típico × volumen) de las barras 15m.
  - **Volumen relativo** (confirmación).

Setup de continuación:
  - ruptura ALCISTA del IB  Y  precio > VWAP  Y  volumen ≥ umbral → **LARGO**
  - ruptura BAJISTA del IB  Y  precio < VWAP  Y  volumen ≥ umbral → **CORTO**
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import MARKET_TZ, now_utc
from services.bar_15m_service import _f, _r4, _volume_ratio, _vwap
from services.initial_balance_service import InitialBalanceService


class VwapIbService:
    def __init__(self, bar_repo, latest_tick_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("vwap_ib", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("horas", 48))

    def _vol_min(self) -> float:
        return float(self._cfg().get("vol_min", 1.0))

    def _max(self) -> int:
        return int(self._cfg().get("max", 10))

    def _stocks(self) -> list[str]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def scan(self, limit: Optional[int] = None) -> list[dict]:
        tope = int(limit) if limit else self._max()
        desde = now_utc() - timedelta(hours=self._horas())
        vol_min = self._vol_min()
        filas = []
        for symbol in self._stocks():
            barras = self.bar_repo.fetch_barras(symbol, desde)
            if len(barras) < 2:
                continue
            close = _f(barras[-1].get("close"))
            if close is None:
                continue
            vwap_list = _vwap(barras)
            vwap = vwap_list[-1] if vwap_list else None
            vol_ratio = _volume_ratio(barras, 10)
            ib = InitialBalanceService.evaluar(symbol, barras, MARKET_TZ, 30)
            ruptura = ib.get("ruptura") if ib else None

            setup = self.setup(ruptura, close, vwap, vol_ratio, vol_min)
            if setup is None:
                continue

            dist_vwap = ((close - vwap) / vwap * 100.0) if vwap else None
            filas.append(
                {
                    "symbol": symbol,
                    "ticker": symbol.split(":")[-1],
                    "close": _r4(close),
                    "ruptura": ruptura,  # ALCISTA / BAJISTA
                    "lado": "LARGO" if ruptura == "ALCISTA" else "CORTO",
                    "ib_high": ib.get("ib_high") if ib else None,
                    "ib_low": ib.get("ib_low") if ib else None,
                    "vwap": _r4(vwap),
                    "dist_vwap": _r4(dist_vwap),
                    "vol_ratio": _r4(vol_ratio),
                    "hora_utc": ib.get("hora_utc") if ib else "",
                }
            )

        filas.sort(key=lambda r: -(r["vol_ratio"] or 0))
        return filas[:tope]

    # ── cálculo puro (testeable) ─────────────────────────────────────────────
    @staticmethod
    def setup(
        ruptura: Optional[str],
        close: Optional[float],
        vwap: Optional[float],
        vol_ratio: Optional[float],
        vol_min: float = 1.0,
    ) -> Optional[dict]:
        """Setup de continuación IB + VWAP + volumen; `None` si no aplica."""
        if ruptura not in ("ALCISTA", "BAJISTA") or close is None or vwap is None:
            return None
        if vol_ratio is None or vol_ratio < vol_min:
            return None
        if ruptura == "ALCISTA" and close > vwap:
            return {"lado": "LARGO", "setup": "IB UP + VWAP + vol"}
        if ruptura == "BAJISTA" and close < vwap:
            return {"lado": "CORTO", "setup": "IB DOWN + VWAP + vol"}
        return None