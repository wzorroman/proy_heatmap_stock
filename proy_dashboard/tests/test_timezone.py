"""Tests de core.timezone — utilidades UTC / zona de mercado."""

from datetime import datetime, timedelta, timezone

from core.settings import load_settings
from core.timezone import (
    UTC,
    age_seconds,
    ensure_utc,
    fase_sesion,
    get_tz,
    is_stale,
    now_utc,
    to_market_tz,
)


def test_get_tz_valida_y_fallback():
    assert get_tz("America/New_York").key == "America/New_York"
    # nombre inexistente → UTC (degradación, no crash)
    assert get_tz("No/Existe").key == "UTC"


def test_now_utc_es_aware():
    dt = now_utc()
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timedelta(0)


def test_ensure_utc_normaliza_naive():
    naive = datetime(2026, 9, 30, 12, 0, 0)
    assert ensure_utc(naive).tzinfo == UTC
    aware = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert ensure_utc(aware).hour == 17


def test_to_market_tz_usa_settings(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    dt = datetime(2026, 9, 30, 16, 0, 0, tzinfo=UTC)
    local = to_market_tz(dt, settings)

    assert local.tzinfo is not None
    assert local.tzinfo.key == "America/New_York"
    # 16:00 UTC en EDT (septiembre) = 12:00
    assert local.hour == 12


def test_age_y_stale():
    hace_20_min = now_utc() - timedelta(minutes=20)
    assert age_seconds(hace_20_min) >= 1190
    assert is_stale(hace_20_min, max_age_seconds=600) is True
    assert is_stale(hace_20_min, max_age_seconds=3600) is False


def test_fase_sesion():
    base = datetime(2026, 9, 30, 13, 30, 0, tzinfo=UTC)  # 09:30 ET
    cierre = datetime(2026, 9, 30, 20, 0, 0, tzinfo=UTC)  # 16:00 ET
    assert fase_sesion(base - timedelta(hours=1), base, cierre) == "PRE"
    assert fase_sesion(base + timedelta(hours=1), base, cierre) == "OPEN"
    assert fase_sesion(cierre + timedelta(hours=1), base, cierre) == "POST"
    assert fase_sesion(cierre + timedelta(hours=6), base, cierre) == "CLOSED"
    assert fase_sesion(base, None, cierre) == "SIN_DATOS"
