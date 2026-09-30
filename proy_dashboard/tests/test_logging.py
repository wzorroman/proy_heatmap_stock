"""Tests de core.logging_config — logging con rotación diaria (patrón proy_heatmap)."""

import logging
from dataclasses import replace

from core.logging_config import build_history_namer, get_logger, setup_global_logging
from core.settings import load_settings


def _settings_con_log_dir(clean_env, empty_env_file, config_file, tmp_path):
    clean_env.setenv("FILE_PATH_LOG", str(tmp_path))
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    return replace(settings, log_dir=tmp_path)


def test_setup_crea_archivo_y_loguea(clean_env, empty_env_file, config_file, tmp_path):
    settings = _settings_con_log_dir(clean_env, empty_env_file, config_file, tmp_path)

    logger, log_path = setup_global_logging(settings)

    assert logger.name == "app"
    assert log_path == str(tmp_path / "app_daily_proy_dashboard_101.log")

    logger.info("mensaje de prueba")
    contenido = (tmp_path / "app_daily_proy_dashboard_101.log").read_text(encoding="utf-8")

    assert "mensaje de prueba" in contenido
    assert "INICIO DE APLICACIÓN" in contenido
    assert settings.version in contenido


def test_get_logger_namespace_app():
    assert get_logger("db").name == "app.db"
    assert get_logger("web.app").name == "app.web.app"


def test_handlers_rotacion_y_consola(clean_env, empty_env_file, config_file, tmp_path):
    from logging.handlers import TimedRotatingFileHandler

    settings = _settings_con_log_dir(clean_env, empty_env_file, config_file, tmp_path)
    logger, _ = setup_global_logging(settings)

    assert any(isinstance(h, TimedRotatingFileHandler) for h in logger.handlers)
    assert any(isinstance(h, logging.StreamHandler) and not isinstance(h, TimedRotatingFileHandler)
               for h in logger.handlers)
    # Idempotencia: no acumula handlers al reconfigurar
    setup_global_logging(settings)
    assert len(logging.getLogger("app").handlers) == 2


def test_history_namer_renombra(clean_env, empty_env_file, config_file, tmp_path):
    settings = _settings_con_log_dir(clean_env, empty_env_file, config_file, tmp_path)
    namer = build_history_namer(settings)

    origen = str(tmp_path / "app_daily_proy_dashboard_101.log.2026-09-29")
    destino = namer(origen)

    assert destino == str(tmp_path / "2026-09-29_app_history_proy_dashboard_101.log")
    # Un nombre no rotado se deja igual
    assert namer("otro.log") == "otro.log"
