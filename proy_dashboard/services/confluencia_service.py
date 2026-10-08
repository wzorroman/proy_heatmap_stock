"""services/confluencia_service.py — alineación multi-timeframe 5m/15m/1D.

Para cada acción determina si los tres timeframes están de acuerdo (alcista,
bajista o neutro) y genera un score de confluencia.
"""

from __future__ import annotations

from typing import Optional

from core.settings import Settings
from services.bar_15m_service import _f


class ConfluenciaService:
    def __init__(
        self,
        indicator_repo,
        latest_tick_repo,
        settings: Settings,
    ) -> None:
        self.indicator_repo = indicator_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def scan(
        self,
        symbols: list[str] | None = None,
        vol_map: dict | None = None,
    ) -> list[dict]:
        """Devuelve lista de acciones con su alineación 5m/15m/1D.

        Si `symbols` viene informado, respeta esa lista y su orden (útil para
        alinear la confluencia con el screener); si no, usa todo el universo.

        `vol_map` (opcional) = {symbol: vol_ratio} para añadir la confirmación de
        volumen (`ALTA CONVICCIÓN` vs `VIGILAR`).
        """
        stocks = list(symbols) if symbols else self._stocks()
        if not stocks:
            return []

        tf5_rows = self.indicator_repo.fetch_recent("5", limit=5000, asset_classes=["equity"])
        tf15_rows = self.indicator_repo.fetch_recent("15", limit=5000, asset_classes=["equity"])

        tf5_map = self._latest_per_symbol(tf5_rows)
        tf15_map = self._latest_per_symbol(tf15_rows)

        latest_rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        latest_map = {r["symbol"]: r for r in latest_rows if r.get("symbol")}

        vol_map = vol_map or {}
        resultados = []
        for symbol in stocks:
            latest = latest_map.get(symbol)
            if latest is None:
                continue
            tf5 = tf5_map.get(symbol)
            tf15 = tf15_map.get(symbol)
            fila = self._analizar(symbol, tf5, tf15, latest, vol_map.get(symbol))
            if fila:
                resultados.append(fila)

        # Sin lista explícita: ordenar por score absoluto descendente.
        if not symbols:
            resultados.sort(key=lambda r: (-abs(r["score"]), r["symbol"]))
        return resultados

    def _stocks(self) -> list[str]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        return [r["symbol"] for r in rows if r.get("symbol")]

    def _latest_per_symbol(self, rows: list[dict]) -> dict[str, dict]:
        """Rows vienen ordenados DESC por timestamp; nos quedamos con el primero de cada símbolo."""
        salida: dict[str, dict] = {}
        for r in rows:
            sym = r.get("symbol")
            if sym and sym not in salida:
                salida[sym] = r
        return salida

    def _analizar(
        self,
        symbol: str,
        tf5: Optional[dict],
        tf15: Optional[dict],
        daily: dict,
        vol: Optional[float] = None,
    ) -> dict:
        s5 = self._estado_tf(tf5)
        s15 = self._estado_tf(tf15)
        s1d = self._estado_daily(daily)

        score = s5["signo"] + s15["signo"] + s1d["signo"]

        if score >= 2:
            label, color = "COMPRAR", "verde"
        elif score <= -2:
            label, color = "VENDER", "rojo"
        else:
            label, color = "NEUTRAL", "amarillo"

        # Confirmación por volumen (panel 2.3 "Confluencia + Vol").
        vol_ratio = _f(vol) if vol is not None else None
        setup = None
        if label in ("COMPRAR", "VENDER"):
            direccion = "ALCISTA" if label == "COMPRAR" else "BAJISTA"
            if vol_ratio is not None and vol_ratio >= 1.0:
                setup = f"ALTA CONVICCIÓN {direccion}"
            else:
                setup = "VIGILAR"

        return {
            "symbol": symbol,
            "rsi_5m": s5["rsi"],
            "rsi_15m": s15["rsi"],
            "rsi_1d": s1d["rsi"],
            "signal_5m": s5["label"],
            "signal_15m": s15["label"],
            "signal_1d": s1d["label"],
            "score": score,
            "signal": label,
            "color": color,
            "vol_ratio": vol_ratio,
            "setup": setup,
        }

    def _estado_tf(self, row: Optional[dict]) -> dict:
        """Interpreta un registro de `fact_market_indicator_tf` (5m o 15m)."""
        if row is None:
            return {"signo": 0, "label": "NEUTRAL", "rsi": None}
        change = _f(row.get("change_pct"))
        rsi = _f(row.get("rsi"))

        # RSI extremo puede anular la dirección del cambio
        if rsi is not None and rsi >= 70:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        if rsi is not None and rsi <= 30:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}

        if change is None:
            return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}
        if change > 0:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}
        if change < 0:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}

    def _estado_daily(self, row: dict) -> dict:
        """Interpreta el último tick diario (`latest_market_tick`)."""
        change = _f(row.get("change_pct"))
        rsi = _f(row.get("rsi"))
        if rsi is not None and rsi >= 70:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        if rsi is not None and rsi <= 30:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}

        if change is None:
            return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}
        if change > 0:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}
        if change < 0:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}

    # ── funciones puras para tests ────────────────────────────────────────────
    @staticmethod
    def estado_tf(
        change_pct: Optional[float],
        rsi: Optional[float],
    ) -> dict:
        """Versión estática para testear la interpretación de un TF."""
        if rsi is not None and rsi >= 70:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        if rsi is not None and rsi <= 30:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}
        if change_pct is None:
            return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}
        if change_pct > 0:
            return {"signo": 1, "label": "ALCISTA", "rsi": rsi}
        if change_pct < 0:
            return {"signo": -1, "label": "BAJISTA", "rsi": rsi}
        return {"signo": 0, "label": "NEUTRAL", "rsi": rsi}

    @staticmethod
    def score_confluencia(s5: dict, s15: dict, s1d: dict) -> tuple[int, str, str]:
        """Versión estática para testear el score global."""
        score = s5["signo"] + s15["signo"] + s1d["signo"]
        if score >= 2:
            return score, "COMPRAR", "verde"
        if score <= -2:
            return score, "VENDER", "rojo"
        return score, "NEUTRAL", "amarillo"
