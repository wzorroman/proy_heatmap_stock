"""services/indicator_service.py — indicadores por activo e histogramas."""

from __future__ import annotations

from typing import Optional

from core.settings import Settings

# nombre lógico → columna (base 1D en latest_market_tick / tf en indicator_tf)
_FIELD_1D = {"rsi": "rsi", "adx": "adx_15", "cci20": "cci20_15", "bbpower": "bbpower_15"}
_FIELD_TF = {"rsi": "rsi", "adx": "adx", "cci20": "cci20", "bbpower": "bbpower"}


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


class IndicatorService:
    def __init__(self, latest_tick_repo, indicator_repo, settings: Settings) -> None:
        self.latest_tick_repo = latest_tick_repo
        self.indicator_repo = indicator_repo
        self.settings = settings

    def _stocks(self) -> list[str]:
        """Clases de activo consideradas acciones (config `universe.stocks`)."""
        return self.settings.business("universe", "stocks", default=["equity", "common"])

    def _valores(self, nombre: str, tf: str = "1d") -> list[dict]:
        if tf in ("1d", "1", "D", "diario"):
            field = _FIELD_1D.get(nombre)
            if field is None:
                return []
            rows = self.latest_tick_repo.fetch_all(asset_classes=self._stocks())
            data = [{"symbol": r["symbol"], "valor": _f(r.get(field))} for r in rows]
        else:
            field = _FIELD_TF.get(nombre)
            if field is None:
                return []
            rows = self.indicator_repo.fetch_recent(
                str(tf), limit=5000, asset_classes=self._stocks()
            )
            vistos: set[int] = set()
            data = []
            for r in rows:
                if r["asset_id"] in vistos:
                    continue
                vistos.add(r["asset_id"])
                data.append({"symbol": r["symbol"], "valor": _f(r.get(field))})

        data = [d for d in data if d["valor"] is not None]
        data.sort(key=lambda d: d["valor"], reverse=True)
        return data

    def por_indicador(self, nombre: str, tf: str = "1d", n: Optional[int] = None) -> list[dict]:
        n = int(n or self.settings.business("panels", "top_n", default=15))
        return self._valores(nombre, tf)[:n]

    def extremos(
        self,
        nombre: str = "rsi",
        tf: str = "1d",
        alto: float = 70.0,
        bajo: float = 30.0,
    ) -> dict:
        """Activos en los límites del indicador (p. ej. RSI ≥70 y ≤30)."""
        data = self._valores(nombre, tf)  # ordenado descendente
        return {
            "sobrecompra": [d for d in data if d["valor"] >= alto],
            "sobreventa": list(reversed([d for d in data if d["valor"] <= bajo])),
            "total": len(data),
        }

    def histograma(self, nombre: str, tf: str = "1d", bins: int = 10) -> dict:
        valores = [d["valor"] for d in self._valores(nombre, tf)]
        if not valores:
            return {"edges": [], "counts": [], "n": 0}
        lo, hi = min(valores), max(valores)
        if hi == lo:
            hi = lo + 1.0
        ancho = (hi - lo) / bins
        counts = [0] * bins
        for v in valores:
            idx = min(bins - 1, int((v - lo) / ancho))
            counts[idx] += 1
        edges = [lo + i * ancho for i in range(bins + 1)]
        return {"edges": edges, "counts": counts, "n": len(valores)}
