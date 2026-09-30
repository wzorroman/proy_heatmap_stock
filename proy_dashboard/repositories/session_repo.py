"""repositories/session_repo.py — sesiones de trading (XNYS)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from repositories.base import BaseRepository


class SessionRepository(BaseRepository):
    def estado_sesion(self, dia: date) -> Optional[dict]:
        return self.fetch_one(
            "SELECT session_date, is_session, is_early_close, opens_at, closes_at "
            "FROM dim_trading_session WHERE session_date = %s",
            (dia,),
        )
