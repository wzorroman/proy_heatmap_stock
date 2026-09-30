"""services/initial_balance_service.py — breakout del rango inicial (09:30–10:00 NY).

Alcances:
  - ``scan_por_accion(symbols)``: evalúa cada acción del universo y detecta si
    rompió su propio rango inicial (IB_high / IB_low).
  - ``evaluar_symbol(symbol)``: IB de un símbolo; usado para mostrar la pastilla
    IB en las tarjetas de precio (SPY / QQQ / IWM).
  - ``scan_mercado()``: utilidad que evalúa los índices de referencia.

El rango inicial se forma con las barras de 15m de la apertura regular
(09:30–10:00 NY por defecto). La ruptura se marca cuando el cierre de una barra
posterior supera el borde del rango.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta, time
from typing import Optional

from core.settings import Settings
from core.timezone import ensure_utc, get_tz, now_utc
from services.bar_15m_service import Bar15mService, _f, _r4

HORA_APERTURA = time(9, 30)
MERCADO_DEFAULT = ["AMEX:SPY", "NASDAQ:QQQ", "AMEX:IWM"]


class InitialBalanceService:
    def __init__(self, bar_repo, latest_tick_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    # ── configuración ────────────────────────────────────────────────────────
    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _ib_minutos(self) -> int:
        return int(self._cfg().get("ib_minutos", 30))

    def ib_minutos(self) -> int:
        """Ventana del rango inicial en minutos (público para las vistas)."""
        return self._ib_minutos()

    def _horas(self) -> int:
        return int(self._cfg().get("ib_horas", 48))

    def _stale_min(self) -> int:
        return int(self._cfg().get("stale_min", 60))

    def _max_acciones(self) -> int:
        return int(self._cfg().get("ib_max_acciones", 15))

    def mercado_simbolos(self) -> list[str]:
        """Símbolos de referencia cuyo IB se muestra en las tarjetas de precio."""
        return list(self._cfg().get("ib_mercado_simbolos") or MERCADO_DEFAULT)

    # ── API pública ──────────────────────────────────────────────────────────
    def evaluar_lote(self, symbols: list[str]) -> dict[str, dict]:
        """Rango inicial por símbolo, **sin reordenar ni truncar**.

        Devuelve un mapa ``{symbol: fila}`` para alinear el IB con la lista del
        screener (mismo orden e idéntico conjunto de filas). Los símbolos sin IB
        evaluable simplemente no aparecen en el mapa.
        """
        desde = now_utc() - timedelta(hours=self._horas())
        out: dict[str, dict] = {}
        for symbol in symbols:
            barras = self._barras(symbol, desde)
            fila = self.evaluar(
                symbol, barras, self.settings.timezone, self._ib_minutos()
            )
            if fila:
                out[symbol] = fila
        return out

    def scan_por_accion(self, symbols: list[str] | None = None) -> dict:
        """Rupturas de rango inicial por acción (prioriza las que rompieron)."""
        stocks = list(symbols) if symbols else self._stocks()
        filas = list(self.evaluar_lote(stocks).values())

        rupturas = [f for f in filas if f["ruptura"] in ("ALCISTA", "BAJISTA")]
        rupturas.sort(key=lambda f: -f["fuerza_pct"])
        dentro = [f for f in filas if f["ruptura"] == "DENTRO"]

        top = rupturas[: self._max_acciones()]
        if not top:
            top = dentro[: self._max_acciones()]

        return {
            "filas": top,
            "total": len(filas),
            "n_rupturas": len(rupturas),
            "ib_minutos": self._ib_minutos(),
        }

    def scan_mercado(self) -> dict:
        """Rango inicial de los índices de referencia."""
        filas = [
            fila
            for symbol in self.mercado_simbolos()
            if (fila := self.evaluar_symbol(symbol))
        ]
        return {"filas": filas, "ib_minutos": self._ib_minutos()}

    def evaluar_symbol(self, symbol: str) -> Optional[dict]:
        """Rango inicial de un único símbolo (sin cambiar la ventana configurada)."""
        desde = now_utc() - timedelta(hours=self._horas())
        barras = self._barras(symbol, desde)
        return self.evaluar(symbol, barras, self.settings.timezone, self._ib_minutos())

    # ── internos ─────────────────────────────────────────────────────────────
    def _stocks(self) -> list[str]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def _barras(self, symbol: str, desde) -> list[dict]:
        barras = self.bar_repo.fetch_barras(symbol, desde)
        if self._necesita_fallback(barras):
            ticks = self.bar_repo.fetch_ticks(symbol, desde)
            if ticks:
                barras = Bar15mService.ensamblar_ticks(ticks)
        return [
            b
            for b in barras
            if all(_f(b.get(k)) is not None for k in ("open", "high", "low", "close"))
        ]

    def _necesita_fallback(self, barras: list[dict]) -> bool:
        if not barras:
            return True
        max_ts = max(ensure_utc(b["timestamp_utc"]) for b in barras)
        return (now_utc() - max_ts) > timedelta(minutes=self._stale_min())

    # ── cálculo puro (testeable sin BD) ──────────────────────────────────────
    @staticmethod
    def evaluar(
        symbol: str,
        barras: list[dict],
        tz_name: str = "America/New_York",
        ib_minutos: int = 30,
    ) -> Optional[dict]:
        """Evalúa el rango inicial de un símbolo sobre sus barras 15m."""
        if len(barras) < 2:
            return None

        tz = get_tz(tz_name)
        inicio_min = HORA_APERTURA.hour * 60 + HORA_APERTURA.minute
        fin_min = inicio_min + int(ib_minutos)
        fin_ib = time(fin_min // 60, fin_min % 60)

        por_dia: dict = defaultdict(list)
        for b in barras:
            local = ensure_utc(b["timestamp_utc"]).astimezone(tz)
            por_dia[local.date()].append((local, b))

        for dia in sorted(por_dia, reverse=True):
            items = sorted(por_dia[dia], key=lambda x: x[0])
            ib_bars = [(l, b) for l, b in items if HORA_APERTURA <= l.time() < fin_ib]
            if not ib_bars:
                continue

            ib_high = max(_f(b["high"]) for _, b in ib_bars)
            ib_low = min(_f(b["low"]) for _, b in ib_bars)
            ib_close = _f(ib_bars[-1][1]["close"])

            ruptura, fuerza, hora, close_act = "DENTRO", 0.0, None, None
            for l, b in items:
                if l.time() < fin_ib:
                    continue
                c = _f(b["close"])
                if c is None:
                    continue
                close_act = c
                if c > ib_high:
                    ruptura = "ALCISTA"
                    fuerza = ((c - ib_high) / ib_high * 100.0) if ib_high else 0.0
                    hora = l.strftime("%H:%M")
                    break
                if c < ib_low:
                    ruptura = "BAJISTA"
                    fuerza = ((ib_low - c) / ib_low * 100.0) if ib_low else 0.0
                    hora = l.strftime("%H:%M")
                    break

            if close_act is None:
                close_act = ib_close

            return {
                "symbol": symbol,
                "ticker": symbol.split(":")[-1],
                "fecha": dia.isoformat(),
                "ib_high": _r4(ib_high),
                "ib_low": _r4(ib_low),
                "close": _r4(close_act),
                "ruptura": ruptura,
                "fuerza_pct": _r4(fuerza),
                "hora": hora or "",
            }
        return None
