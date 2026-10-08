"""services/divergencia_5m_service.py — divergencias precio / RSI 5m.

Misma lógica que `DivergenciaService` pero sobre **barras de 5 minutos**,
ensambladas desde los ticks de `fact_market_series` (no hay tabla materializada
de barras 5m).

  - Divergencia BAJISTA: precio hace un máximo más alto y el RSI uno más bajo.
  - Divergencia ALCISTA: precio hace un mínimo más bajo y el RSI uno más alto.

El RSI se calcula sobre los cierres de las barras 5m (Wilder, periodo 14).
"""

from __future__ import annotations

from datetime import timedelta

from core.settings import Settings
from core.timezone import ensure_utc, now_utc
from services.bar_15m_service import Bar15mService, _f
from services.divergencia_service import DivergenciaService


class Divergencia5mService:
    def __init__(self, bar_repo, latest_tick_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        # Config bajo bloque dedicado `divergencia_5m` con fallback a `divergencia`.
        return (
            self.settings.business("divergencia_5m")
            or self.settings.business("trading_15m", default={})
        )

    def _ventana_horas(self) -> int:
        # Más lookback porque las barras 5m cubren más tiempo; por defecto 24h.
        return int(self._cfg().get("ventana_horas", 24))

    def _pivote_k(self) -> int:
        return int(self._cfg().get("pivote_k", 3))

    def _rsi_min(self) -> float:
        return float(self._cfg().get("rsi_min", 3.0))

    def _min_sep(self) -> int:
        # En barras 5m, mínimo de separación entre pivotes (en nº de barras).
        return int(self._cfg().get("min_sep", 8))

    def _max(self) -> int:
        return int(self._cfg().get("max", 12))

    def _rsi_periodo(self) -> int:
        return int(self._cfg().get("rsi_periodo", 14))

    def _stocks(self) -> list[str]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def scan(self, symbols: list[str] | None = None) -> list[dict]:
        """Detecta divergencias precio/RSI en 5m para los símbolos dados."""
        stocks = list(symbols) if symbols else self._stocks()
        desde = now_utc() - timedelta(hours=self._ventana_horas())
        filas = []
        for symbol in stocks:
            filas_fila = self._detectar_symbol(symbol, desde)
            if filas_fila:
                filas.append(filas_fila)
        filas.sort(key=lambda r: -abs(r["rsi_delta"]))
        return filas[: self._max()]

    def _detectar_symbol(self, symbol: str, desde) -> dict | None:
        ticks = self.bar_repo.fetch_ticks(symbol, desde)
        barras = Bar15mService.ensamblar_ticks_5m(ticks)
        # Limpieza: OHLCV con no-nulos.
        barras = [
            {"high": b["high"], "low": b["low"], "close": b["close"]}
            for b in barras
            if all(_f(b.get(k)) is not None for k in ("high", "low", "close"))
        ]
        if len(barras) < 20:
            return None
        return DivergenciaService.detectar(
            symbol,
            barras,
            k=self._pivote_k(),
            rsi_min=self._rsi_min(),
            min_sep=self._min_sep(),
            periodo=self._rsi_periodo(),
        )