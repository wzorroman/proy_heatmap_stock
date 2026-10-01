"""services/event_service.py — calendario económico y sorpresas."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import ensure_utc, now_utc, rango_dia_utc


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


# Niveles de importancia del calendario (TradingView): 1 = alta, 2 = media, 3 = baja.
# El valor "todos" desactiva el filtro. Mapeo a la columna `importance` (-1/0/1).
NIVEL_IMPORTANCIA = {"1": 1, "2": 0, "3": -1}


def nivel_a_importancia(nivel) -> Optional[int]:
    if nivel is None:
        return None
    nivel = str(nivel).strip().lower()
    if nivel in ("", "todos", "all"):
        return None
    return NIVEL_IMPORTANCIA.get(nivel)


class EventService:
    def __init__(self, events_repo, settings: Settings) -> None:
        self.events_repo = events_repo
        self.settings = settings

    def _cfg(self, clave: str, default):
        return self.settings.business("events", clave, default=default)

    def _a_dict(self, r: dict, ahora: datetime) -> dict:
        ts = ensure_utc(r["event_timestamp"])
        return {
            "event_id": r["event_id"],
            "title": r.get("title"),
            "country": r.get("country"),
            "categoria": r.get("category"),
            "importance": r.get("importance"),
            "event_timestamp": ts.isoformat(),
            "actual": r.get("actual_display") or r.get("actual"),
            "forecast": r.get("forecast_display") or r.get("forecast"),
            "previous": r.get("previous_display") or r.get("previous"),
            "sorpresa_pct": self._sorpresa(r),
            "pasado": ts < ahora,
        }

    def _sorpresa(self, r: dict) -> Optional[float]:
        actual = _f(r.get("actual_raw"))
        forecast = _f(r.get("forecast_raw"))
        if actual is None or forecast is None or forecast == 0:
            return None
        return (actual - forecast) / abs(forecast) * 100.0

    def proximos(
        self,
        country: Optional[str] = None,
        importance_min: Optional[int] = None,
        horas: Optional[int] = None,
    ) -> list[dict]:
        ahora = now_utc()
        if importance_min is None:
            importance_min = self._cfg("importance_min", 0)
        if country is None:
            country = self._cfg("default_country", "ALL")
        lookahead = int(horas or self._cfg("lookahead_hours", 72))
        rows = self.events_repo.fetch_eventos(
            country=country,
            importance_min=importance_min,
            since=ahora - timedelta(hours=int(self._cfg("lookback_hours", 24))),
            until=ahora + timedelta(hours=lookahead),
        )
        return [self._a_dict(r, ahora) for r in rows]

    def eventos_del_dia(
        self, country: Optional[str] = None, nivel: Optional[str] = None
    ) -> list[dict]:
        """Eventos del **día local** (zona de visualización), pasados y por venir.

        El filtro se hace contra la columna UTC `event_timestamp`: se toma la fecha
        en `APP_TIMEZONE` (default `America/New_York`), se convierte su medianoche a
        UTC y se filtra por esa ventana `[inicio, fin)`. La hora se muestra luego en
        la misma zona.

        `country`: ISO-2 o "ALL" (todos). `nivel`: "todos" | "1" (alta) |
        "2" (media) | "3" (baja). Por defecto, los de mayor importancia.
        """
        if country is None:
            country = self._cfg("today_country", "ALL")
        if nivel is None:
            nivel = self._cfg("today_importance_level", 1)
        importancia = nivel_a_importancia(nivel)

        ahora = now_utc()
        inicio, fin = rango_dia_utc(ahora, self.settings.timezone)

        rows = self.events_repo.fetch_eventos(
            country=country,
            importance=importancia,
            since=inicio,
            until=fin,
            limit=200,
        )
        return [self._a_dict(r, ahora) for r in rows]

    def paises(self) -> list[str]:
        """Países disponibles en el calendario (ISO-2)."""
        return self.events_repo.paises()

    def sorpresas(self, country: Optional[str] = None, importance_min: Optional[int] = None) -> list[dict]:
        rows = self.events_repo.fetch_eventos(
            country=country if country else "ALL",
            importance_min=importance_min,
            limit=500,
        )
        ahora = now_utc()
        con_sorpresa = []
        for r in rows:
            d = self._a_dict(r, ahora)
            if d["sorpresa_pct"] is not None:
                con_sorpresa.append(d)
        con_sorpresa.sort(key=lambda d: abs(d["sorpresa_pct"]), reverse=True)
        return con_sorpresa
