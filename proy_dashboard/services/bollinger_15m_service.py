"""services/bollinger_15m_service.py — reversión en Bollinger 15m.

Panel 2.2 del roadmap: "Reversión en Bollinger 15m — Pinchazos de Banda + Volumen".

Detecta acciones que tocan o se acercan a las bandas de Bollinger (20, 2) en 15m
con volumen por encima de la media:

  - RECHAZO HIGH: el precio toca/supera la banda superior → posible reversión bajista.
  - REBOTE LOW:   el precio toca/perfora la banda inferior → posible rebote alcista.

Es una señal de reversión (contra el movimiento), complementaria al panel 2.1
que busca continuación de tendencia.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import now_utc
from services.bar_15m_service import _bollinger, _f, _r4, _volume_ratio


class Bollinger15mService:
    def __init__(self, bar_repo, latest_tick_repo, settings: Settings) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("bollinger_horas", 48))

    def _max(self) -> int:
        return int(self._cfg().get("bollinger_max", 5))

    def _ventana(self) -> int:
        return int(self._cfg().get("bollinger_ventana", 20))

    def _k(self) -> float:
        return float(self._cfg().get("bollinger_k", 2.0))

    def _tol_sigma(self) -> float:
        """Proximidad a la banda en desviaciones estándar (σ)."""
        return float(self._cfg().get("bollinger_tol_sigma", 0.5))

    def _vol_min(self) -> float:
        return float(self._cfg().get("bollinger_vol_min", 1.0))

    def scan(self, limit: Optional[int] = None) -> list[dict]:
        """Devuelve las reversiones en banda ordenadas por score.

        `limit` sobreescribe el máximo configurado (`bollinger_max`); útil para
        vistas con más puntos (p. ej. el dot-plot).
        """
        tope = int(limit) if limit else self._max()
        desde = now_utc() - timedelta(hours=self._horas())
        stocks = self._stocks()
        if not stocks:
            return []

        latest_bars = self.bar_repo.fetch_latest_per_symbol(stocks, desde)
        con_barra = {b["symbol"] for b in latest_bars}

        filas = []
        for symbol in stocks:
            if symbol not in con_barra:
                continue
            row = self._analizar_symbol(symbol, desde)
            if row:
                filas.append(row)

        filas.sort(key=lambda r: -r["score"])
        return filas[:tope]

    def _stocks(self) -> list[str]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def _analizar_symbol(self, symbol: str, desde) -> Optional[dict]:
        barras = self.bar_repo.fetch_barras(symbol, desde)
        if len(barras) < self._ventana() + 1:
            return None

        closes = [_f(b.get("close")) for b in barras]
        close = closes[-1]
        if close is None:
            return None

        k = self._k()
        upper, middle, lower = _bollinger(closes, self._ventana(), k)
        u, m, l = upper[-1], middle[-1], lower[-1]
        if u is None or l is None:
            return None

        # σ implícita de las bandas: upper = SMA20 + k·σ  →  σ = (upper − SMA20)/k.
        std = (u - m) / k if k else 0.0

        # Solo extremos: precio dentro de `tol_sigma` σ de una banda, o que la superó.
        deteccion = self.clasificar_banda(close, u, l, std, self._tol_sigma())
        if deteccion is None:
            return None
        tipo, lado, nota, dist_banda, supero = deteccion
        estado = "ACCIONABLE" if supero else "CERCA"

        vol_ratio = _volume_ratio(barras, 10)
        if vol_ratio is None or vol_ratio < self._vol_min():
            return None

        prev = closes[-2] if len(closes) >= 2 else None
        change_pct = ((close - prev) / prev * 100.0) if prev else 0.0
        rsi_15, _ = self._latest_indicators(symbol)

        # Posición en la banda en desviaciones estándar (σ):
        #   +k = banda superior, 0 = SMA20 (media), -k = banda inferior.
        z_banda = ((close - m) / std) if std else 0.0

        return {
            "symbol": symbol,
            "ticker": symbol.split(":")[-1],
            "close": _r4(close),
            "change_pct": _r4(change_pct),
            "upper": _r4(u),
            "middle": _r4(m),
            "lower": _r4(l),
            "dist_banda": _r4(dist_banda),
            "z_banda": _r4(z_banda),
            "vol_ratio": _r4(vol_ratio),
            "rsi_15": _r4(rsi_15),
            "tipo": tipo,
            "lado": lado,
            "nota": nota,
            "estado": estado,
            "score": _r4(self._score(vol_ratio, dist_banda)),
        }

    def _latest_indicators(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        ticker = symbol.split(":")[-1]
        for r in rows:
            if r.get("symbol") == symbol or r.get("symbol", "").split(":")[-1] == ticker:
                return _f(r.get("rsi_15")), _f(r.get("adx_15"))
        return None, None

    def _score(self, vol_ratio: Optional[float], dist_banda: Optional[float]) -> float:
        """Mayor volumen y mayor penetración de la banda = señal más fuerte."""
        s = (vol_ratio or 0.0) * 2.0
        if dist_banda is not None:
            s += max(0.0, dist_banda)
        return s

    # ── cálculo puro (testeable) ─────────────────────────────────────────────
    @staticmethod
    def clasificar_banda(
        close: Optional[float],
        upper: Optional[float],
        lower: Optional[float],
        std: Optional[float],
        tol_sigma: float = 0.5,
    ) -> Optional[tuple[str, str, str, float, bool]]:
        """Clasifica la proximidad a una banda **en unidades de σ**.

        Solo acepta extremos: precio dentro de `tol_sigma` σ de una banda o que
        la haya superado. La distancia se mide en σ (no en % de precio), así el
        filtro es invariante a la volatilidad del activo.

        Devuelve `(tipo, lado, nota, dist_banda_pct, supero)` o `None`:
          - `dist_banda_pct`: penetración respecto a la banda en %.
          - `supero`: `True` si el precio perforó la banda (accionable),
            `False` si quedó dentro de `tol_sigma` σ (watchlist / "cerca").
        """
        if close is None or upper is None or lower is None or not std or std <= 0:
            return None
        # Distancia a la banda superior/inferior en σ (positiva = aún dentro).
        if (upper - close) / std <= tol_sigma:
            supero = close > upper
            dist = (close - upper) / upper * 100.0
            nota = "sobre banda superior" if supero else "cerca banda superior"
            return "RECHAZO HIGH", "CORTO", nota, dist, supero
        if (close - lower) / std <= tol_sigma:
            supero = close < lower
            dist = (lower - close) / lower * 100.0
            nota = "bajo banda inferior" if supero else "cerca banda inferior"
            return "REBOTE LOW", "LARGO", nota, dist, supero
        return None
