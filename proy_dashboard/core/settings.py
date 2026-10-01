"""core/settings.py — configuración única del dashboard.

Precedencia (D19):
  - `.env`            → infraestructura y secretos (BD, puerto, TZ, logging).
  - `config_dashboard.json` → parámetros de negocio (pesos, zonas, umbrales).

El resto del código consume una única instancia de `Settings` (vía `get_settings()`),
nunca lee `os.environ` ni el JSON directamente. Cero números mágicos.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROJECT_PATH = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_PATH / ".env"
DEFAULT_CONFIG_FILE = PROJECT_PATH / "config_dashboard.json"

# Versión de la aplicación (D17). Subir al cerrar cada fase.
VERSION = "1.0.21"


def _get(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_int(key: str, default: int) -> int:
    value = _get(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    value = _get(key)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _get_tz(key: str, default: str) -> str:
    """Nombre de zona horaria válido; si falta o no existe, usa `default`.

    `APP_TIMEZONE` es preferencia de visualización: ante un valor ausente o
    inválido se cae a `America/New_York` (zona de mercado), nunca a UTC.
    """
    nombre = _get(key, default) or default
    try:
        ZoneInfo(nombre)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return default
    return nombre


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    # metadata
    version: str
    project_path: Path
    config_path: Path
    # aplicación
    app_name: str
    app_env: str
    port: int
    timezone: str
    # logging
    log_dir: Path
    retransmisor_id: str
    log_level: str
    log_backup_days: int
    # base de datos (None si no está configurada → degradación)
    db_host: Optional[str]
    db_port: int
    db_name: Optional[str]
    db_user: Optional[str]
    db_password: Optional[str]
    db_write_enabled: bool
    # negocio (config_dashboard.json)
    config: dict

    @property
    def db_configurada(self) -> bool:
        return all([self.db_host, self.db_name, self.db_user, self.db_password])

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in ("dev", "development", "local")

    def business(self, *keys: str, default: Any = None) -> Any:
        """Acceso anidado a config_dashboard.json.

        Ejemplo: settings.business("score", "zones", "comprar", default=6.5)
        """
        node: Any = self.config
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def db_kwargs(self) -> dict:
        """kwargs listos para PostgreSQLConnector."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
        }


def load_settings(
    env_file: Optional[Path | str] = None,
    config_path: Optional[Path | str] = None,
) -> Settings:
    """Carga `.env` + `config_dashboard.json` y construye `Settings`.

    Parámetros pensados para tests (aislar rutas). `load_dotenv` no sobreescribe
    variables ya presentes en el entorno, así que `monkeypatch.setenv` manda.
    """
    load_dotenv(env_file or DEFAULT_ENV_FILE)

    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
    config = json.loads(cfg_path.read_text(encoding="utf-8"))

    log_dir = Path(_get("FILE_PATH_LOG", "./logs") or "./logs")
    if not log_dir.is_absolute():
        log_dir = PROJECT_PATH / log_dir

    return Settings(
        version=_get("APP_VERSION", VERSION) or VERSION,
        project_path=PROJECT_PATH,
        config_path=cfg_path,
        app_name=_get("APP_NAME", "proy_dashboard") or "proy_dashboard",
        app_env=_get("APP_ENV", "dev") or "dev",
        port=_get_int("APP_PORT", 8100),
        timezone=_get_tz("APP_TIMEZONE", "America/New_York"),
        log_dir=log_dir,
        retransmisor_id=_get("RETRANSMISOR_ID", "101") or "101",
        log_level=(_get("LOG_LEVEL", "INFO") or "INFO").upper(),
        log_backup_days=_get_int("LOG_BACKUP_DAYS", 14),
        db_host=_get("BD_HEATMAP_HOST"),
        db_port=_get_int("BD_HEATMAP_PORT", 5432),
        db_name=_get("BD_HEATMAP_DATABASE"),
        db_user=_get("BD_HEATMAP_USER"),
        db_password=_get("BD_HEATMAP_PASSWORD"),
        db_write_enabled=_get_bool("DB_WRITE_ENABLED", True),
        config=config,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instancia única (cacheada). Usar `get_settings.cache_clear()` en tests."""
    return load_settings()
