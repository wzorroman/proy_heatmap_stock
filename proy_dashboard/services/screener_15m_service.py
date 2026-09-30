"""services/screener_15m_service.py — scanner de oportunidades en acciones a 15 min.

Para cada equity con datos recientes calcula:
  - cambio % de la última barra 15m
  - volumen relativo vs media de las últimas barras
  - distancia al VWAP
  - RSI 15m y ADX 15m

Y emite una señal COMPRAR / VENDER / NEUTRAL.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from core.settings import Settings
from core.timezone import now_utc
from services.bar_15m_service import _f, _r4, _vwap, _volume_ratio


class Screener15mService:
    def __init__(
        self,
        bar_repo,
        latest_tick_repo,
        settings: Settings,
    ) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("screener_horas", 48))

    def scan(self) -> list[dict]:
        """Devuelve lista de acciones con señal 15m."""
        desde = now_utc() - timedelta(hours=self._horas())
        stocks = self._stocks()
        if not stocks:
            return []

        latest_bars = self.bar_repo.fetch_latest_per_symbol(stocks, desde)
        bar_map = {b["symbol"]: b for b in latest_bars}

        resultados = []
        for symbol in stocks:
            bar = bar_map.get(symbol)
            if bar is None:
                continue
            row = self._analizar_symbol(symbol, bar, desde)
            if row:
                resultados.append(row)

        # Ordenar por fuerza de señal: COMPRAR > VENDER > NEUTRAL, luego por |change|
        orden = {"COMPRAR": 0, "VENDER": 1, "NEUTRAL": 2}
        resultados.sort(
            key=lambda r: (orden.get(r["signal"], 9), -abs(r.get("change_pct") or 0))
        )
        return resultados

    def _stocks(self) -> list[str]:
        """Universo equity del último tick."""
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def _analizar_symbol(self, symbol: str, bar: dict, desde) -> Optional[dict]:
        # Traemos las barras recientes para calcular volumen relativo y vwap
        barras = self.bar_repo.fetch_barras(symbol, desde)
        if len(barras) < 2:
            return None

        closes = [_f(b["close"]) for b in barras]
        vwap_list = _vwap(barras)
        vol_ratio = _volume_ratio(barras, 10)

        close = _f(bar.get("close"))
        prev_close = closes[-2] if len(closes) >= 2 else None
        change_pct = ((close - prev_close) / prev_close * 100.0) if close and prev_close else 0.0
        vwap = vwap_list[-1] if vwap_list else None
        dist_vwap = ((close - vwap) / vwap * 100.0) if close and vwap else None

        rsi_15, adx_15 = self._latest_indicators(symbol)
        signal = self._signal(close, vwap, vol_ratio, rsi_15, adx_15)

        return {
            "symbol": symbol,
            "close": _r4(close),
            "change_pct": _r4(change_pct),
            "vwap": _r4(vwap),
            "dist_vwap": _r4(dist_vwap),
            "vol_ratio": _r4(vol_ratio),
            "rsi_15": rsi_15,
            "adx_15": adx_15,
            "signal": signal,
        }

    def _latest_indicators(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        ticker = symbol.split(":")[-1]
        for r in rows:
            if r.get("symbol") == symbol or r.get("symbol", "").split(":")[-1] == ticker:
                return _f(r.get("rsi_15")), _f(r.get("adx_15"))
        return None, None

    def _signal(
        self,
        close: Optional[float],
        vwap: Optional[float],
        vol_ratio: Optional[float],
        rsi: Optional[float],
        adx: Optional[float],
    ) -> str:
        cfg = self._cfg()
        sobrecompra = float(cfg.get("rsi_sobrecompra", 70))
        sobreventa = float(cfg.get("rsi_sobreventa", 30))
        adx_min = float(cfg.get("adx_min", 20))
        vol_min = float(cfg.get("vol_ratio_min", 1.0))

        if close is None or vwap is None:
            return "NEUTRAL"

        arriba_vwap = close > vwap
        tendencia = adx is not None and adx >= adx_min
        volumen = vol_ratio is not None and vol_ratio >= vol_min

        if arriba_vwap and tendencia and volumen and rsi is not None and rsi < sobrecompra:
            return "COMPRAR"
        if (not arriba_vwap) and tendencia and volumen and rsi is not None and rsi > sobreventa:
            return "VENDER"
        return "NEUTRAL"

    # ── funciones puras para tests ────────────────────────────────────────────
    @staticmethod
    def calc_signal(
        close: Optional[float],
        vwap: Optional[float],
        vol_ratio: Optional[float],
        rsi: Optional[float],
        adx: Optional[float],
        cfg: Optional[dict] = None,
    ) -> str:
        """Versión estática para testear la lógica de señal."""
        cfg = cfg or {}
        sobrecompra = float(cfg.get("rsi_sobrecompra", 70))
        sobreventa = float(cfg.get("rsi_sobreventa", 30))
        adx_min = float(cfg.get("adx_min", 20))
        vol_min = float(cfg.get("vol_ratio_min", 1.0))

        if close is None or vwap is None:
            return "NEUTRAL"
        arriba_vwap = close > vwap
        tendencia = adx is not None and adx >= adx_min
        volumen = vol_ratio is not None and vol_ratio >= vol_min
        if arriba_vwap and tendencia and volumen and rsi is not None and rsi < sobrecompra:
            return "COMPRAR"
        if (not arriba_vwap) and tendencia and volumen and rsi is not None and rsi > sobreventa:
            return "VENDER"
        return "NEUTRAL"
