"""services/health_service.py — estado de módulos y frescura de datos."""

from __future__ import annotations

from typing import Optional

from core.settings import Settings
from core.timezone import age_seconds, now_utc
from db.postgresql_connection import check_connection


def _estado_frescura(ts, limite_s: float) -> dict:
    if ts is None:
        return {"estado": "WARN", "edad_s": None, "timestamp_utc": None}
    edad = age_seconds(ts)
    return {
        "estado": "OK" if edad < limite_s else "WARN",
        "edad_s": round(edad, 1),
        "timestamp_utc": ts.isoformat(),
    }


class HealthService:
    def __init__(
        self,
        settings: Settings,
        latest_tick_repo,
        heatmap_repo,
        events_repo,
        indicator_repo=None,
    ) -> None:
        self.settings = settings
        self.latest_tick_repo = latest_tick_repo
        self.heatmap_repo = heatmap_repo
        self.events_repo = events_repo
        self.indicator_repo = indicator_repo

    def check(self) -> dict:
        limite_s = float(self.settings.business("app", "stale_warn_min", default=10)) * 60.0

        db_ok, db_detalle = check_connection(self.settings)
        db_estado = "OK" if db_ok else ("WARN" if not self.settings.db_configurada else "ERROR")

        modulos = {
            "db": {"estado": db_estado, "detalle": db_detalle},
            "data": _estado_frescura(self.latest_tick_repo.max_timestamp(), limite_s),
            "heatmap": _estado_frescura(self.heatmap_repo.max_timestamp(), limite_s * 3),
            "events": _estado_frescura(self.events_repo.max_timestamp(), 24 * 3600.0),
        }

        global_estado = "OK" if all(m.get("estado") == "OK" for m in modulos.values()) else "WARN"
        return {
            "status": global_estado,
            "app": {
                "name": self.settings.app_name,
                "version": self.settings.version,
                "env": self.settings.app_env,
            },
            "modulos": modulos,
            "timestamp_utc": now_utc().isoformat(),
        }

    def db_ok(self) -> tuple[bool, str]:
        return check_connection(self.settings)
