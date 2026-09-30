"""core/logging_config.py — logging global con rotación diaria.

Réplica del patrón `proy_heatmap/utils/config_logging.py`:
  - logger raíz de la app: ``app`` (los módulos usan ``get_logger(__name__)``).
  - formatter: ``%(asctime)s - [%(name)s:%(lineno)s] - %(levelname)s - %(message)s``.
  - archivo ``app_daily_{APP_NAME}_{RETRANSMISOR_ID}.log`` con `TimedRotatingFileHandler`
    (rotación a medianoche, retención ``LOG_BACKUP_DAYS``).
  - ``namer`` que renombra los rotados a ``YYYY-MM-DD_app_history_{APP_NAME}_{ID}.log``.
  - consola (stdout) + archivo.

Única adaptación respecto al original: lee de ``core.settings`` y la inicialización
es explícita (``setup_global_logging()``) en vez de ejecutarse al importar, para
evitar efectos secundarios al importar en tests.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Tuple

from core.settings import Settings, get_settings

LOG_FORMAT = "%(asctime)s - [%(name)s:%(lineno)s] - %(levelname)s - %(message)s"


def build_history_namer(settings: Settings):
    """Devuelve el `namer` que renombra los archivos rotados.

    De: ``app_daily_proy_dashboard_101.log.2026-09-29``
    A:  ``2026-09-29_app_history_proy_dashboard_101.log``
    """

    def history_namer(default_name: str) -> str:
        if ".log." not in os.path.basename(default_name):
            return default_name
        base_name = os.path.basename(default_name)
        dir_name = os.path.dirname(default_name)
        _, date_part = base_name.split(".log.", 1)
        return os.path.join(
            dir_name,
            f"{date_part}_app_history_{settings.app_name}_{settings.retransmisor_id}.log",
        )

    return history_namer


def setup_global_logging(settings: Optional[Settings] = None) -> Tuple[logging.Logger, str]:
    """Configura el logger ``app``. Idempotente (limpia handlers previos)."""
    settings = settings or get_settings()

    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    logger.propagate = False
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    log_path = log_dir / f"app_daily_{settings.app_name}_{settings.retransmisor_id}.log"
    daily_handler = TimedRotatingFileHandler(
        str(log_path),
        when="midnight",
        interval=1,
        backupCount=settings.log_backup_days,
        encoding="utf-8",
    )
    daily_handler.namer = build_history_namer(settings)
    daily_handler.setFormatter(formatter)
    daily_handler.setLevel(getattr(logging, settings.log_level, logging.INFO))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, settings.log_level, logging.INFO))

    logger.addHandler(daily_handler)
    logger.addHandler(console_handler)

    logger.info("=== INICIO DE APLICACIÓN (v%s) ===", settings.version)
    logger.info("Logging configurado en: %s", log_path)

    return logger, str(log_path)


def get_logger(name: str) -> logging.Logger:
    """Logger de módulo bajo el namespace ``app`` (ej. ``app.web.app``)."""
    return logging.getLogger(f"app.{name}")
