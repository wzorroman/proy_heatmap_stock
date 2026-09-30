"""Fixtures comunes de los tests (aislamiento de entorno y rutas)."""

import json
from pathlib import Path

import pytest

PROJECT_PATH = Path(__file__).resolve().parent.parent
REAL_CONFIG = PROJECT_PATH / "config_dashboard.json"

ENV_KEYS = [
    "APP_VERSION",
    "APP_NAME",
    "APP_ENV",
    "APP_PORT",
    "APP_TIMEZONE",
    "FILE_PATH_LOG",
    "RETRANSMISOR_ID",
    "LOG_LEVEL",
    "LOG_BACKUP_DAYS",
    "DB_WRITE_ENABLED",
    "BD_HEATMAP_HOST",
    "BD_HEATMAP_PORT",
    "BD_HEATMAP_DATABASE",
    "BD_HEATMAP_USER",
    "BD_HEATMAP_PASSWORD",
]


@pytest.fixture
def clean_env(monkeypatch):
    """Elimina de os.environ las claves que afectan a Settings."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def empty_env_file(tmp_path):
    env_file = tmp_path / "empty.env"
    env_file.write_text("", encoding="utf-8")
    return env_file


@pytest.fixture
def config_file(tmp_path):
    """Copia de config_dashboard.json en tmp (aislada)."""
    data = json.loads(REAL_CONFIG.read_text(encoding="utf-8"))
    path = tmp_path / "config_dashboard.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def live_connector():
    """Conector a la BD real (heatmap_stock). Se salta si no está accesible."""
    from core.settings import get_settings
    from db.postgresql_connection import PostgreSQLConnector, check_connection

    settings = get_settings()
    if not settings.db_configurada:
        pytest.skip("BD no configurada (.env)")
    ok, detalle = check_connection(settings)
    if not ok:
        pytest.skip(f"BD no accesible: {detalle}")
    connector = PostgreSQLConnector(**settings.db_kwargs())
    yield connector
    connector.disconnect()


@pytest.fixture
def docker_connector():
    """Conector a la BD scratch local del docker (heatmap_stock_test, migración 0009)."""
    from db.postgresql_connection import PostgreSQLConnector

    connector = PostgreSQLConnector(
        host="localhost", port=5432, database="heatmap_stock_test",
        user="postgres", password="postgres", connect_timeout=3,
    )
    if not connector.connect():
        pytest.skip("docker heatmap_stock_test no accesible")
    yield connector
    connector.disconnect()
