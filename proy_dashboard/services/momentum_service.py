"""services/momentum_service.py — momentum top/bottom del último tick."""

from __future__ import annotations

from typing import Optional

from core.settings import Settings


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


class MomentumService:
    def __init__(self, latest_tick_repo, settings: Settings) -> None:
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def top_bottom(self, n: Optional[int] = None) -> dict:
        n = int(n or self.settings.business("panels", "top_n", default=15))
        rows = self.latest_tick_repo.fetch_all()

        movimientos = []
        for r in rows:
            change = _f(r.get("change_pct"))
            if change is None:
                continue
            close = _f(r.get("close"))
            prev_close = None
            if close is not None and change != -100:
                prev_close = close / (1.0 + change / 100.0)
            movimientos.append(
                {
                    "symbol": r["symbol"],
                    "asset_class": r.get("asset_class"),
                    "change_pct": change,
                    "close": close,
                    "prev_close": round(prev_close, 4) if prev_close is not None else None,
                    "rsi": _f(r.get("rsi")),
                    "adx": _f(r.get("adx_15")),
                }
            )
        movimientos.sort(key=lambda m: m["change_pct"], reverse=True)
        top = movimientos[:n]
        bottom = list(reversed(movimientos[-n:])) if movimientos else []
        return {"top": top, "bottom": bottom, "n": len(movimientos)}

    def change_rsi(self, n: Optional[int] = None) -> list[dict]:
        """Puntos (símbolo, change %, RSI) de acciones para 'Change vs RSI'."""
        clases = self.settings.business("universe", "stocks", default=["equity", "common"])
        rows = self.latest_tick_repo.fetch_all(asset_classes=clases)
        salida = []
        for r in rows:
            change = _f(r.get("change_pct"))
            rsi = _f(r.get("rsi"))
            if change is None or rsi is None:
                continue
            salida.append({"symbol": r["symbol"], "change_pct": change, "rsi": rsi})
        salida.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
        return salida[:n] if n else salida
