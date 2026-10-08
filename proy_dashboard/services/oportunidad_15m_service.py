"""services/oportunidad_15m_service.py — oportunidades de momentum 15m.

Panel 2.1 del roadmap: "Oportunidades Momentum 15m — Continuación con Volumen".

Detecta acciones en continuación alcista a 15 minutos:
  - Precio por encima del VWAP (momentum intradía positivo).
  - RSI(15) en zona de fuerza (50–70, no sobrecompra extrema).
  - ADX(15) ≥ umbral (tendencia fuerte).
  - Volumen relativo ≥ umbral (confirmación).
  - La última barra es alcista o plana (change_pct >= 0) — buscamos continuidad,
    no reversión.

El resultado son hasta N oportunidades ordenadas por fuerza (puntaje interno).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import now_utc
from services.bar_15m_service import _f, _r4, _vwap, _volume_ratio


class Oportunidad15mService:
    def __init__(self, bar_repo, latest_tick_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("oportunidad_horas", 48))

    def _max(self) -> int:
        return int(self._cfg().get("oportunidad_max", 4))

    def _rsi_min(self) -> float:
        return float(self._cfg().get("oportunidad_rsi_min", 50))

    def _rsi_max(self) -> float:
        return float(self._cfg().get("oportunidad_rsi_max", 70))

    def _adx_min(self) -> float:
        return float(self._cfg().get("oportunidad_adx_min", 25))

    def _vol_min(self) -> float:
        return float(self._cfg().get("oportunidad_vol_min", 1.2))

    def scan(self) -> list[dict]:
        """Devuelve hasta `_max()` oportunidades de largo 15m ordenadas por score."""
        desde = now_utc() - timedelta(hours=self._horas())
        stocks = self._stocks()
        if not stocks:
            return []

        latest_bars = self.bar_repo.fetch_latest_per_symbol(stocks, desde)
        bar_map = {b["symbol"]: b for b in latest_bars}

        oportunidades = []
        for symbol in stocks:
            bar = bar_map.get(symbol)
            if bar is None:
                continue
            row = self._analizar_symbol(symbol, bar, desde)
            if row:
                oportunidades.append(row)

        # Mayor score primero
        oportunidades.sort(key=lambda r: -r["score"])
        return oportunidades[: self._max()]

    def _stocks(self) -> list[str]:
        """Universo equity del último tick."""
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def _analizar_symbol(self, symbol: str, bar: dict, desde) -> Optional[dict]:
        barras = self.bar_repo.fetch_barras(symbol, desde)
        if len(barras) < 2:
            return None

        close = _f(bar.get("close"))
        if close is None:
            return None

        closes = [_f(b["close"]) for b in barras]
        prev_close = closes[-2] if len(closes) >= 2 else None
        change_pct = ((close - prev_close) / prev_close * 100.0) if prev_close else 0.0

        vwap_list = _vwap(barras)
        vwap = vwap_list[-1] if vwap_list else None
        dist_vwap = ((close - vwap) / vwap * 100.0) if vwap else None

        vol_ratio = _volume_ratio(barras, 10)
        rsi_15, adx_15 = self._latest_indicators(symbol)

        if not self._cumple(close, vwap, vol_ratio, rsi_15, adx_15, change_pct):
            return None

        score = self._score(
            rsi=rsi_15,
            adx=adx_15,
            vol_ratio=vol_ratio,
            dist_vwap=dist_vwap,
            change_pct=change_pct,
        )

        return {
            "symbol": symbol,
            "ticker": symbol.split(":")[-1],
            "close": _r4(close),
            "change_pct": _r4(change_pct),
            "vwap": _r4(vwap),
            "dist_vwap": _r4(dist_vwap),
            "vol_ratio": _r4(vol_ratio),
            "rsi_15": _r4(rsi_15),
            "adx_15": _r4(adx_15),
            "score": _r4(score),
        }

    def _latest_indicators(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        ticker = symbol.split(":")[-1]
        for r in rows:
            if r.get("symbol") == symbol or r.get("symbol", "").split(":")[-1] == ticker:
                return _f(r.get("rsi_15")), _f(r.get("adx_15"))
        return None, None

    def _cumple(
        self,
        close: Optional[float],
        vwap: Optional[float],
        vol_ratio: Optional[float],
        rsi: Optional[float],
        adx: Optional[float],
        change_pct: float,
    ) -> bool:
        if close is None or vwap is None or close <= vwap:
            return False
        if vol_ratio is None or vol_ratio < self._vol_min():
            return False
        if rsi is None or not (self._rsi_min() <= rsi <= self._rsi_max()):
            return False
        if adx is None or adx < self._adx_min():
            return False
        # Buscamos continuidad alcista, no reversión desde abajo.
        if change_pct < 0:
            return False
        return True

    def _score(
        self,
        rsi: Optional[float],
        adx: Optional[float],
        vol_ratio: Optional[float],
        dist_vwap: Optional[float],
        change_pct: float,
    ) -> float:
        """Puntaje simple: cuanto más fuerte la tendencia y volumen, mayor score."""
        s = 0.0
        if rsi is not None:
            # RSI en el medio del rango 50-70 da más puntos que en los extremos
            s += 10 - abs(rsi - 60) / 2.0
        if adx is not None:
            s += adx / 5.0
        if vol_ratio is not None:
            s += vol_ratio * 2.0
        if dist_vwap is not None:
            s += dist_vwap
        s += change_pct
        return s
