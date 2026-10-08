"""services/heatmap_service.py — treemap, sectorial y rotación."""

from __future__ import annotations

from core.settings import Settings


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


class HeatmapService:
    def __init__(self, heatmap_repo, settings: Settings) -> None:
        self.heatmap_repo = heatmap_repo
        self.settings = settings

    def _stocks(self) -> list[str]:
        """Clases de activo consideradas acciones (config `universe.stocks`)."""
        return self.settings.business("universe", "stocks", default=["equity", "common"])

    def treemap(self, limite: int | None = None) -> list[dict]:
        limite = int(limite or self.settings.business("panels", "treemap_max", default=1000))
        rows = self.heatmap_repo.fetch_latest(limit=limite, asset_classes=self._stocks())
        return [
            {
                "symbol": r["symbol"],
                "name": r.get("company_name") or r["symbol"],
                "sector": r.get("sector"),
                "value": _f(r.get("market_cap")),
                "change_pct": _f(r.get("daily_change_pct")),
                "price": _f(r.get("price_heatmap")),
                "volatility": _f(r.get("volatility_d")),
                "high_52w": _f(r.get("high_52w")),
                "low_52w": _f(r.get("low_52w")),
                "volume": _f(r.get("volume")),
                "avg_vol_10d": _f(r.get("avg_vol_10d")),
            }
            for r in rows
        ]

    def sectores(self) -> list[dict]:
        min_activos = int(self.settings.business("panels", "sector_min_assets", default=5))
        rows = self.heatmap_repo.sectores(min_activos=min_activos)
        return [
            {
                "sector": r["sector"] or "Sin sector",
                "n_activos": int(r["n_activos"]),
                "change_medio": _f(r.get("change_medio")),
                "market_cap_total": _f(r.get("market_cap_total")),
                "ganadores": int(r.get("ganadores") or 0),
                "perdedores": int(r.get("perdedores") or 0),
                "vol_medio": _f(r.get("vol_medio")),
            }
            for r in rows
        ]

    def sector_risk(self) -> list[dict]:
        """Sector Risk Gauge: señal 0–100 (bajo = COMPRAR, alto = VENDER)."""
        escala = float(self.settings.business("panels", "sector_signal_scale", default=15))
        salida = []
        for s in self.sectores():
            ch = s.get("change_medio") or 0.0
            signal = max(0.0, min(100.0, 50.0 + ch * escala))
            if signal < 35:
                label, color = "COMPRAR", "verde"
            elif signal < 65:
                label, color = "NEUTRAL", "amarillo"
            else:
                label, color = "VENDER", "rojo"
            salida.append(
                {
                    "sector": s["sector"],
                    "signal": round(signal, 1),
                    "rend": s.get("change_medio"),
                    "vol": s.get("vol_medio"),
                    "label": label,
                    "color": color,
                }
            )
        salida.sort(key=lambda x: x["signal"], reverse=True)
        return salida

    def sectores_lista(self) -> list[dict]:
        filas = [
            {"sector": r["sector"] or "Sin sector", "n": int(r["n"])}
            for r in self.heatmap_repo.fetch_sectores(min_activos=1)
        ]
        filas.sort(key=lambda s: s["sector"].lower())
        return filas

    def tabla_sector(self, sector: str | None = None, q: str | None = None) -> dict:
        """Tabla de stocks de un sector (o búsqueda por símbolo). Default: tecnología."""
        lista = self.sectores_lista()
        nombres = [s["sector"] for s in lista]
        por_defecto = self.settings.business(
            "tabla_sector", "default", default="Technology Services"
        )
        actual = sector or por_defecto
        if actual not in nombres and lista:
            actual = lista[0]["sector"]
        limite = int(self.settings.business("tabla_sector", "limite", default=60))
        consulta = (q or "").strip()
        if consulta:
            filas = self.heatmap_repo.buscar_stocks(
                consulta, asset_classes=self._stocks(), limit=limite
            )
        else:
            filas = self.heatmap_repo.fetch_por_sector(
                actual, asset_classes=self._stocks(), limit=limite
            )
        return {"sector": actual, "q": consulta, "sectores": lista, "filas": filas}

    def rotacion(self) -> list[dict]:
        ventanas = int(self.settings.business("panels", "heatmap_windows", default=12))
        rows = self.heatmap_repo.rotacion(ventanas=ventanas)
        return [
            {
                "timestamp_utc": r["timestamp_utc"],
                "n_activos": int(r["n_activos"]),
                "change_medio": _f(r.get("change_medio")),
            }
            for r in rows
        ]

    def distribucion_change(self) -> list[float]:
        return self.heatmap_repo.distribucion_change()

    def top_equity_rsi(self, n: int | None = None) -> list[dict]:
        """Acciones de mayor capitalización EN OPORTUNIDAD (RSI ≥60 o ≤40)."""
        n = int(n or self.settings.business("rsi", "scatter_max", default=100))
        alto = self.settings.business("rsi", "oportunidad_alto", default=60)
        bajo = self.settings.business("rsi", "oportunidad_bajo", default=40)
        rows = self.heatmap_repo.top_equity_rsi(
            limit=n,
            asset_classes=self._stocks(),
            rsi_alto=alto,
            rsi_bajo=bajo,
        )
        return [
            {
                "symbol": r["symbol"],
                "name": r.get("company_name") or r["symbol"],
                "sector": r.get("sector"),
                "rsi": _f(r.get("rsi")),
                "market_cap": _f(r.get("market_cap")),
                "change_pct": _f(r.get("daily_change_pct")),
            }
            for r in rows
            if _f(r.get("rsi")) is not None
        ]
