"""services/divergencia_service.py — divergencias precio / RSI 15m.

Para cada acción detecta pivotes locales de precio y compara los dos últimos
extremos con su RSI 15m:

  - Divergencia BAJISTA: precio hace un máximo más alto y el RSI uno más bajo.
  - Divergencia ALCISTA: precio hace un mínimo más bajo y el RSI uno más alto.

El RSI se calcula sobre los cierres de las barras 15m (Wilder, periodo 14).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import ensure_utc, now_utc
from services.bar_15m_service import Bar15mService, _f, _r4


class DivergenciaService:
    def __init__(self, bar_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.settings = settings

    # ── configuración ────────────────────────────────────────────────────────
    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("div_horas", 48))

    def _pivote_k(self) -> int:
        return int(self._cfg().get("div_pivote_k", 2))

    def _rsi_min(self) -> float:
        return float(self._cfg().get("div_rsi_min", 1.5))

    def _max(self) -> int:
        return int(self._cfg().get("div_max", 15))

    def _stale_min(self) -> int:
        return int(self._cfg().get("stale_min", 60))

    # ── API ──────────────────────────────────────────────────────────────────
    def scan(self, symbols: list[str] | None = None) -> dict:
        stocks = list(symbols) if symbols else self._stocks()
        desde = now_utc() - timedelta(hours=self._horas())
        filas = []
        for symbol in stocks:
            barras = self._barras(symbol, desde)
            if len(barras) < 20:
                continue
            fila = self.detectar(
                symbol, barras, k=self._pivote_k(), rsi_min=self._rsi_min()
            )
            if fila:
                filas.append(fila)

        filas.sort(key=lambda r: -abs(r["rsi_delta"]))
        return {"filas": filas[: self._max()], "total": len(stocks)}

    # ── internos ─────────────────────────────────────────────────────────────
    def _stocks(self) -> list[str]:
        return []

    def _barras(self, symbol: str, desde) -> list[dict]:
        barras = self.bar_repo.fetch_barras(symbol, desde)
        if self._necesita_fallback(barras):
            ticks = self.bar_repo.fetch_ticks(symbol, desde)
            if ticks:
                barras = Bar15mService.ensamblar_ticks(ticks)
        return [
            b
            for b in barras
            if all(_f(b.get(k)) is not None for k in ("high", "low", "close"))
        ]

    def _necesita_fallback(self, barras: list[dict]) -> bool:
        if not barras:
            return True
        max_ts = max(ensure_utc(b["timestamp_utc"]) for b in barras)
        return (now_utc() - max_ts) > timedelta(minutes=self._stale_min())

    # ── cálculo puro (testeable) ─────────────────────────────────────────────
    @staticmethod
    def rsi_serie(closes: list[Optional[float]], periodo: int = 14) -> list[Optional[float]]:
        """RSI de Wilder sobre una serie de cierres."""
        salida: list[Optional[float]] = [None] * len(closes)
        if len(closes) <= periodo:
            return salida
        gains, losses = 0.0, 0.0
        for i in range(1, periodo + 1):
            diff = closes[i] - closes[i - 1]
            gains += max(diff, 0.0)
            losses += max(-diff, 0.0)
        avg_gain, avg_loss = gains / periodo, losses / periodo
        salida[periodo] = 100.0 - 100.0 / (1.0 + (avg_gain / avg_loss if avg_loss else float("inf")))
        for i in range(periodo + 1, len(closes)):
            diff = closes[i] - closes[i - 1]
            avg_gain = (avg_gain * (periodo - 1) + max(diff, 0.0)) / periodo
            avg_loss = (avg_loss * (periodo - 1) + max(-diff, 0.0)) / periodo
            salida[i] = 100.0 - 100.0 / (1.0 + (avg_gain / avg_loss if avg_loss else float("inf")))
        return salida

    @staticmethod
    def _pivotes(valores: list[float], k: int) -> list[int]:
        idx = []
        for i in range(k, len(valores) - k):
            ventana = valores[i - k : i + k + 1]
            if valores[i] == max(ventana):
                idx.append(i)
        return idx

    @staticmethod
    def _pivotes_bajos(valores: list[float], k: int) -> list[int]:
        idx = []
        for i in range(k, len(valores) - k):
            ventana = valores[i - k : i + k + 1]
            if valores[i] == min(ventana):
                idx.append(i)
        return idx

    @staticmethod
    def detectar(
        symbol: str,
        barras: list[dict],
        k: int = 2,
        rsi_min: float = 3.0,
        min_sep: int = 5,
        periodo: int = 14,
    ) -> Optional[dict]:
        highs = [_f(b.get("high")) for b in barras]
        lows = [_f(b.get("low")) for b in barras]
        closes = [_f(b.get("close")) for b in barras]
        if any(v is None for v in highs + lows + closes):
            return None
        rsi = DivergenciaService.rsi_serie(closes, periodo)

        def fila(tipo, i1, i2, v1, v2, r1, r2):
            delta_p = (v2 - v1) / v1 * 100.0 if v1 else 0.0
            return {
                "symbol": symbol,
                "ticker": symbol.split(":")[-1],
                "tipo": tipo,
                "p1": _r4(v1),
                "p2": _r4(v2),
                "precio_delta": _r4(delta_p),
                "rsi1": _r4(r1),
                "rsi2": _r4(r2),
                "rsi_delta": _r4(r2 - r1),
            }

        altos = DivergenciaService._pivotes(highs, k)
        if len(altos) >= 2:
            i1, i2 = altos[-2], altos[-1]
            r1, r2 = rsi[i1], rsi[i2]
            if (
                i2 - i1 >= min_sep
                and r1 is not None
                and r2 is not None
                and highs[i2] > highs[i1]
                and r2 < r1 - rsi_min
            ):
                return fila("BAJISTA", i1, i2, highs[i1], highs[i2], r1, r2)

        bajos = DivergenciaService._pivotes_bajos(lows, k)
        if len(bajos) >= 2:
            j1, j2 = bajos[-2], bajos[-1]
            r1, r2 = rsi[j1], rsi[j2]
            if (
                j2 - j1 >= min_sep
                and r1 is not None
                and r2 is not None
                and lows[j2] < lows[j1]
                and r2 > r1 + rsi_min
            ):
                return fila("ALCISTA", j1, j2, lows[j1], lows[j2], r1, r2)

        return None
