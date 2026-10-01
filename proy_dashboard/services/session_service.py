"""services/session_service.py — fase de la sesión de mercado."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.settings import Settings
from core.timezone import ensure_utc, fase_sesion, now_utc, to_market_tz


class SessionService:
    def __init__(self, session_repo, settings: Settings) -> None:
        self.session_repo = session_repo
        self.settings = settings

    def estado(self, ahora: Optional[datetime] = None) -> dict:
        ahora = ensure_utc(ahora or now_utc())
        local = to_market_tz(ahora)
        fila = self.session_repo.estado_sesion(local.date())
        if not fila:
            return {"fase": "SIN_DATOS", "is_session": None, "session_date": local.date().isoformat()}
        return {
            "fase": fase_sesion(ahora, fila.get("opens_at"), fila.get("closes_at")),
            "is_session": fila.get("is_session"),
            "is_early_close": fila.get("is_early_close"),
            "session_date": fila["session_date"].isoformat(),
            "opens_at": fila.get("opens_at").isoformat() if fila.get("opens_at") else None,
            "closes_at": fila.get("closes_at").isoformat() if fila.get("closes_at") else None,
        }
