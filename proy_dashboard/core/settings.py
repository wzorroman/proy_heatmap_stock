"""core/settings.py — configuración única del dashboard.

Precedencia (D19):
  - `.env`            → infraestructura y secretos (BD, puerto, TZ, logging).
  - `config_dashboard.json` → parámetros de negocio (pesos, zonas, umbrales).

El resto del código consume una única instancia de `Settings` (vía `get_settings()`),
nunca lee `os.environ` ni el JSON directamente. Cero números mágicos.
"""

from __future__ import annotations

import copy
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
# Config por gráfico: un JSON por gráfico (A1, A2, ...). Se fusionan sobre el
# config global en orden de nombre de archivo.
DEFAULT_CHARTS_DIR = PROJECT_PATH / "config" / "charts"

# Versión de la aplicación (D17). Subir al cerrar cada fase.
VERSION = "2.1.0"


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

    def chart_meta(self, slug: str) -> dict:
        """Metadatos de un gráfico (código, título) declarados en config/charts/*.json."""
        meta = self.config.get("meta")
        if not isinstance(meta, dict):
            return {}
        return meta.get(slug) or {}

    def chart_code(self, slug: str) -> str:
        """Código identificador del gráfico (A1, A2, …); '' si no está declarado."""
        return str(self.chart_meta(slug).get("codigo") or "")

    def chart_title(self, slug: str, default: str = "") -> str:
        """Título declarado del gráfico; `default` si no está definido."""
        return str(self.chart_meta(slug).get("titulo") or default)

    def chart_tf(self, slug: str) -> str:
        """Tiempo de evaluación declarado del gráfico (p. ej. '15m', '1D'); '' si no hay."""
        return str(self.chart_meta(slug).get("tf") or "")

    def chart_help(self, slug: str) -> Optional[str]:
        """Texto de ayuda del gráfico (mapa del popup '(+)'), o None.

        Se declara en ``config/charts/*.json`` como lista de líneas
        (``["  ▲", "  │ …"]``) o como un único string con saltos ``\\n``.
        """
        ayuda = self.chart_meta(slug).get("ayuda")
        if isinstance(ayuda, (list, tuple)):
            return "\n".join(str(linea) for linea in ayuda) or None
        if isinstance(ayuda, str):
            return ayuda.strip("\n") or None
        return None

    def db_kwargs(self) -> dict:
        """kwargs listos para PostgreSQLConnector."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
        }


def _deep_merge(base: dict, extra: dict) -> dict:
    """Fusiona `extra` sobre `base` recursivamente (dicts anidados; el resto pisa)."""
    for key, valor in extra.items():
        if isinstance(valor, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], valor)
        else:
            base[key] = copy.deepcopy(valor)
    return base


def _charts_dir(config_path: Optional[Path]) -> Optional[Path]:
    """Directorio de config por gráfico, derivado de la ruta del config base.

    Soporta `config/charts/` junto al config (producción) y una copia aislada en
    tests. Devuelve `None` si no existe.
    """
    if config_path is not None:
        for candidato in (
            config_path.parent / "charts",
            config_path.parent / "config" / "charts",
        ):
            if candidato.is_dir():
                return candidato
        return None
    return DEFAULT_CHARTS_DIR if DEFAULT_CHARTS_DIR.is_dir() else None


def _load_config(config_path: Optional[Path], charts_dir: Optional[Path] = None) -> dict:
    """Carga el config global y fusiona, en orden de nombre, los JSON por gráfico."""
    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    directorio = charts_dir if charts_dir is not None else _charts_dir(cfg_path)
    if directorio and directorio.is_dir():
        for archivo in sorted(directorio.glob("*.json")):
            config = _deep_merge(config, json.loads(archivo.read_text(encoding="utf-8")))
    return config


def load_settings(
    env_file: Optional[Path | str] = None,
    config_path: Optional[Path | str] = None,
    charts_dir: Optional[Path | str] = None,
) -> Settings:
    """Carga `.env` + config global + `config/charts/*.json` y construye `Settings`.

    Parámetros pensados para tests (aislar rutas). `load_dotenv` no sobreescribe
    variables ya presentes en el entorno, así que `monkeypatch.setenv` manda.
    """
    load_dotenv(env_file or DEFAULT_ENV_FILE)

    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
    charts = Path(charts_dir) if charts_dir else None
    config = _load_config(cfg_path, charts)

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
