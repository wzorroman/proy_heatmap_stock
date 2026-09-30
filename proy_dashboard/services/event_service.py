"""services/event_service.py — calendario económico y sorpresas."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional

from core.settings import Settings
from core.timezone import ensure_utc, get_tz, now_utc


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


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

    def eventos_del_dia(self, importance_min: Optional[int] = None) -> list[dict]:
        """Eventos de HOY (zona de mercado), ya pasados y por venir, de mayor importancia."""
        if importance_min is None:
            importance_min = int(self._cfg("today_importance_min", 1))
        tz = get_tz(self.settings.timezone)
        ahora = now_utc()
        hoy_local = ahora.astimezone(tz).date()
        inicio = datetime.combine(hoy_local, time.min, tzinfo=tz).astimezone(timezone.utc)
        fin = inicio + timedelta(days=1)

        rows = self.events_repo.fetch_eventos(
            importance_min=importance_min,
            since=inicio,
            until=fin,
            limit=200,
        )
        return [self._a_dict(r, ahora) for r in rows]

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
