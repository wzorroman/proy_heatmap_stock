"""Tests de core.timezone — utilidades UTC / zona de mercado."""

from datetime import datetime, timedelta, timezone

from core.settings import load_settings
from core.timezone import (
    MARKET_TZ,
    UTC,
    age_seconds,
    ensure_utc,
    fase_sesion,
    format_hora,
    get_tz,
    is_stale,
    now_utc,
    rango_dia_utc,
    to_market_tz,
    tz_label,
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


def test_to_market_tz_es_siempre_ny(monkeypatch, clean_env, empty_env_file, config_file):
    """La zona de mercado es NY aunque APP_TIMEZONE sea otra (p. ej. Lima).

    `APP_TIMEZONE` es preferencia de visualización; nunca mueve la ventana de
    sesión (apertura 09:30 NY, rango inicial, fases).
    """
    monkeypatch.setenv("APP_TIMEZONE", "America/Lima")
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    assert settings.timezone == "America/Lima"

    dt = datetime(2026, 9, 30, 16, 0, 0, tzinfo=UTC)
    local = to_market_tz(dt)

    assert MARKET_TZ == "America/New_York"
    assert local.tzinfo.key == "America/New_York"
    # 16:00 UTC en EDT (septiembre) = 12:00
    assert local.hour == 12


def test_format_hora_por_zona():
    # 14:00 UTC = 10:00 NY (EDT) = 09:00 Lima
    iso = "2026-09-30T14:00:00+00:00"
    assert format_hora(iso, "America/New_York") == "10:00"
    assert format_hora(iso, "America/Lima") == "09:00"


def test_format_hora_entradas_vacias_o_invalidas():
    assert format_hora("", "America/Lima") == ""
    assert format_hora(None, "America/Lima") == ""
    assert format_hora("no-es-iso", "America/Lima") == ""


def test_tz_label():
    assert tz_label("America/New_York") == "NY"
    assert tz_label("America/Lima") == "PE"
    assert tz_label("Europe/Madrid") == "Madrid"


def test_rango_dia_utc_new_york():
    # 01:00 UTC del 1/oct = 21:00 NY del 30/sep → día local 30/sep
    momento = datetime(2026, 10, 1, 1, 0, 0, tzinfo=UTC)
    inicio, fin = rango_dia_utc(momento, "America/New_York")

    # Medianoche NY (EDT, UTC-4) del 30/sep = 04:00 UTC; fin exclusivo = 04:00 del 1/oct
    assert inicio == datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)
    assert fin == datetime(2026, 10, 1, 4, 0, 0, tzinfo=UTC)
    assert fin - inicio == timedelta(days=1)


def test_rango_dia_utc_lima_difiere_de_ny():
    momento = datetime(2026, 10, 1, 1, 0, 0, tzinfo=UTC)
    inicio_ny, _ = rango_dia_utc(momento, "America/New_York")
    inicio_pe, _ = rango_dia_utc(momento, "America/Lima")

    # Lima es UTC-5: su medianoche cae 1 h después que la de NY
    assert inicio_pe - inicio_ny == timedelta(hours=1)


def test_rango_dia_utc_es_semiabierto():
    """El fin es exclusivo: la medianoche exacta pertenece al día siguiente."""
    momento = datetime(2026, 10, 1, 1, 0, 0, tzinfo=UTC)
    inicio, fin = rango_dia_utc(momento, "America/New_York")

    # Un instante justo en `fin` ya es del día siguiente, no de esta ventana.
    inicio2, fin2 = rango_dia_utc(fin, "America/New_York")
    assert inicio2 == fin
    assert fin2 == fin + timedelta(days=1)
    assert inicio < fin


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
