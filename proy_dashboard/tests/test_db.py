"""Tests del conector PostgreSQL (sin red)."""

import pytest

from db.postgresql_connection import PostgreSQLConnector, check_connection
from core.settings import load_settings


def test_check_connection_no_configurada(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    ok, detalle = check_connection(settings)

    assert ok is False
    assert "no configurada" in detalle


def test_connector_sin_servidor_no_lanza(clean_env, empty_env_file, config_file):
    # Puerto cerrado en localhost: connect() devuelve False sin excepción.
    connector = PostgreSQLConnector(
        host="127.0.0.1", port=1, database="nope", user="nope", password="nope",
        connect_timeout=1,
    )
    try:
        assert connector.connect() is False
    finally:
        connector.disconnect()
