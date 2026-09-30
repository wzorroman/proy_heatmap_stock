"""repositories/events_repo.py — calendario económico."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from repositories.base import BaseRepository

_SELECT = """
SELECT event_id, title, country, category, importance, event_timestamp,
       actual, forecast, previous,
       actual_display, forecast_display, previous_display,
       actual_raw, forecast_raw, currency, unit
FROM fact_economic_event
"""


class EventsRepository(BaseRepository):
    def fetch_eventos(
        self,
        country: Optional[str] = None,
        importance_min: Optional[int] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 200,
    ) -> list[dict]:
        condiciones = []
        params: list = []
        if country and country.upper() != "ALL":
            condiciones.append("country = %s")
            params.append(country.upper())
        if importance_min is not None:
            condiciones.append("importance >= %s")
            params.append(int(importance_min))
        if since is not None:
            condiciones.append("event_timestamp >= %s")
            params.append(since)
        if until is not None:
            condiciones.append("event_timestamp <= %s")
            params.append(until)

        sql = _SELECT
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY event_timestamp LIMIT %s"
        params.append(int(limit))
        return self.fetch(sql, tuple(params))

    def max_timestamp(self) -> Optional[datetime]:
        row = self.fetch_one("SELECT max(event_timestamp) AS ts FROM fact_economic_event")
        return row["ts"] if row else None
