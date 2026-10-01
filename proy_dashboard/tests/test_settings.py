"""Tests de core.settings — configuración única (.env + config_dashboard.json)."""

from core.settings import VERSION, load_settings


def test_defaults_sin_entorno(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)

    assert settings.version == VERSION == "1.0.21"
    assert settings.app_name == "proy_dashboard"
    assert settings.app_env == "dev"
    assert settings.port == 8100
    assert settings.timezone == "America/New_York"
    assert settings.retransmisor_id == "101"
    assert settings.log_level == "INFO"
    assert settings.log_backup_days == 14
    assert settings.db_write_enabled is True
    # Sin variables de BD → no configurada (degradación)
    assert settings.db_configurada is False


def test_env_sobreescribe_defaults(clean_env, empty_env_file, config_file):
    clean_env.setenv("APP_PORT", "9999")
    clean_env.setenv("APP_ENV", "dev")
    clean_env.setenv("BD_HEATMAP_HOST", "localhost")
    clean_env.setenv("BD_HEATMAP_PORT", "5432")
    clean_env.setenv("BD_HEATMAP_DATABASE", "heatmap_stock")
    clean_env.setenv("BD_HEATMAP_USER", "postgres")
    clean_env.setenv("BD_HEATMAP_PASSWORD", "secret")
    clean_env.setenv("DB_WRITE_ENABLED", "false")

    settings = load_settings(env_file=empty_env_file, config_path=config_file)

    assert settings.port == 9999
    assert settings.db_configurada is True
    assert settings.db_write_enabled is False
    assert settings.db_kwargs() == {
        "host": "localhost",
        "port": 5432,
        "database": "heatmap_stock",
        "user": "postgres",
        "password": "secret",
    }


def test_business_acceso_anidado(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)

    assert settings.business("app", "htmx_refresh_ms") == 180000
    assert settings.business("score", "zones", "comprar") == 6.5
    assert settings.business("score", "zones", "vender") == 4.5
    assert settings.business("no", "existe", default="x") == "x"
    # El radar declara 4 componentes (VIX/US10Y/DXY/TLT)
    comps = settings.business("score", "radar", "components")
    assert [c["logical_key"] for c in comps] == ["VIX", "US10Y", "DXY", "TLT"]


def test_timezone_default_new_york(clean_env, empty_env_file, config_file):
    """Sin `APP_TIMEZONE` la zona de visualización es NY."""
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    assert settings.timezone == "America/New_York"


def test_timezone_invalida_cae_a_new_york(clean_env, empty_env_file, config_file):
    """Un `APP_TIMEZONE` inválido no debe degradar a UTC en silencio."""
    clean_env.setenv("APP_TIMEZONE", "No/Existe")
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    assert settings.timezone == "America/New_York"


def test_timezone_valida_se_respeta(clean_env, empty_env_file, config_file):
    clean_env.setenv("APP_TIMEZONE", "America/Lima")
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    assert settings.timezone == "America/Lima"


def test_log_dir_absoluto_con_env(clean_env, empty_env_file, config_file, tmp_path):
    clean_env.setenv("FILE_PATH_LOG", str(tmp_path / "mis_logs"))
    settings = load_settings(env_file=empty_env_file, config_path=config_file)

    assert settings.log_dir == tmp_path / "mis_logs"
    assert settings.log_dir.is_absolute()
