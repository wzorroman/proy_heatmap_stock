"""Tests de core.container — wiring de dependencias."""

from core.container import Container
from core.settings import load_settings
from db.postgresql_connection import PostgreSQLConnector


def test_build_sin_bd(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    container = Container.build(settings=settings)

    assert container.connector is None
    assert container.db_habilitada is False
    assert container.settings is settings
    # close() sin conector no falla
    container.close()


def test_build_con_bd_no_conecta(clean_env, empty_env_file, config_file):
    clean_env.setenv("BD_HEATMAP_HOST", "localhost")
    clean_env.setenv("BD_HEATMAP_DATABASE", "heatmap_stock")
    clean_env.setenv("BD_HEATMAP_USER", "postgres")
    clean_env.setenv("BD_HEATMAP_PASSWORD", "postgres")
    settings = load_settings(env_file=empty_env_file, config_path=config_file)

    container = Container.build(settings=settings, connect=False)

    assert container.db_habilitada is True
    assert isinstance(container.connector, PostgreSQLConnector)
    # no se abrió conexión (connect=False)
    assert container.connector.connection is None
    container.close()


def test_context_manager(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    with Container.build(settings=settings) as container:
        logger = container.logger("test")
        assert logger.name == "app.test"
    assert container.connector is None
