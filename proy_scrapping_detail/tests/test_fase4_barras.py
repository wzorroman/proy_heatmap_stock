# file: proy_scrapping_detail/tests/test_fase4_barras.py
"""Pruebas de la FASE 4 — F4.1b Regla de cierre de barra + agregación 15 min.

Cubre la lógica pura de db/bar_repository.py (sin red ni BD): buckets de
15 min, `close_quality` (M-CAP-03 reformulada), OHLCV, n_ticks, is_regular
y el reporte de calidad.
"""
import os
import sys
from datetime import datetime, date, timedelta, timezone

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from db.bar_repository import (  # noqa: E402
    agrupar_barras,
    bar_cierre_utc,
    bucket_15m_utc,
    close_quality_para_offset,
    es_barra_regular,
    fecha_ny_iso,
    resumen_calidad,
    session_date_para,
    ultimo_tick_offset_s,
)

UTC = timezone.utc
T = datetime

# Sesión XNYS del 2026-09-21 (EDT, UTC-4): 09:30–16:00 ET = 13:30–20:00 UTC
SESION_310 = {
    "2026-09-21": {
        "is_session": True,
        "opens_at": T(2026, 9, 21, 13, 30, tzinfo=UTC),
        "closes_at": T(2026, 9, 21, 20, 0, tzinfo=UTC),
    }
}


# ---------------------------------------------------------------------------
# Buckets de 15 min (fronteras UTC)
# ---------------------------------------------------------------------------

def test_bucket_15m_en_frontera():
    assert bucket_15m_utc(T(2026, 9, 21, 14, 30, tzinfo=UTC)) == \
        T(2026, 9, 21, 14, 30, tzinfo=UTC)


def test_bucket_15m_inicio_de_barra():
    assert bucket_15m_utc(T(2026, 9, 21, 14, 44, 59, tzinfo=UTC)) == \
        T(2026, 9, 21, 14, 30, tzinfo=UTC)


def test_bucket_15m_frontera_siguiente_barra():
    # 14:45:00 pertenece a la barra [14:45, 15:00)
    assert bucket_15m_utc(T(2026, 9, 21, 14, 45, 0, tzinfo=UTC)) == \
        T(2026, 9, 21, 14, 45, tzinfo=UTC)


def test_bucket_15m_naive_se_trata_como_utc():
    assert bucket_15m_utc(T(2026, 9, 21, 14, 33, 0)) == \
        T(2026, 9, 21, 14, 30, tzinfo=UTC)


def test_bar_cierre_es_mas_15_minutos():
    inicio = T(2026, 9, 21, 14, 30, tzinfo=UTC)
    assert bar_cierre_utc(inicio) == T(2026, 9, 21, 14, 45, tzinfo=UTC)


# ---------------------------------------------------------------------------
# F4.1b · Regla de cierre (close_quality) — M-CAP-03 reformulada
# ---------------------------------------------------------------------------

def test_ultimo_tick_offset_s_positivo_si_el_tick_precede():
    cierre = T(2026, 9, 21, 14, 45, 0, tzinfo=UTC)
    assert ultimo_tick_offset_s(cierre, T(2026, 9, 21, 14, 44, 50, tzinfo=UTC)) == 10


def test_ultimo_tick_offset_s_negativo_si_el_tick_es_posterior():
    cierre = T(2026, 9, 21, 14, 45, 0, tzinfo=UTC)
    assert ultimo_tick_offset_s(cierre, T(2026, 9, 21, 14, 45, 10, tzinfo=UTC)) == -10


def test_close_quality_ventana_definitiva():
    # [T-20s, T-5s] → definitive (offset 6..20)
    for offset in (6, 10, 19, 20):
        assert close_quality_para_offset(offset) == "definitive", offset


def test_close_quality_ventana_provisional():
    # [T-5s, T+15s] → provisional (offset -15..5; T-5s cae a provisional)
    for offset in (-15, -10, -1, 0, 1, 5):
        assert close_quality_para_offset(offset) == "provisional", offset


def test_close_quality_fuera_de_rango_unknown():
    for offset in (-16, -30, 21, 60, 180):
        assert close_quality_para_offset(offset) == "unknown", offset


def test_close_quality_equivalencias_con_el_roadmap():
    # Ticks del Ejemplo: T-10s → definitive (muestreo F4.1c), T+10s → provisional
    cierre = T(2026, 9, 21, 14, 45, 0, tzinfo=UTC)
    t10_before = T(2026, 9, 21, 14, 44, 50, tzinfo=UTC)      # T-10s
    t10_after = T(2026, 9, 21, 14, 45, 10, tzinfo=UTC)       # T+10s
    assert close_quality_para_offset(
        ultimo_tick_offset_s(cierre, t10_before)) == "definitive"
    assert close_quality_para_offset(
        ultimo_tick_offset_s(cierre, t10_after)) == "provisional"


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

def test_session_date_utc_de_barra():
    assert session_date_para(T(2026, 9, 21, 14, 30, tzinfo=UTC)) == date(2026, 9, 21)


def test_fecha_ny_iso():
    # 2026-09-21 14:30 UTC = 10:30 ET → misma fecha
    assert fecha_ny_iso(T(2026, 9, 21, 14, 30, tzinfo=UTC)) == "2026-09-21"


def test_is_regular_equity_dentro_de_sesion():
    barra = T(2026, 9, 21, 14, 30, tzinfo=UTC)
    assert es_barra_regular("equity", barra, SESION_310) is True


def test_is_regular_equity_fuera_de_sesion():
    barra = T(2026, 9, 21, 20, 15, tzinfo=UTC)
    assert es_barra_regular("equity", barra, SESION_310) is False


def test_is_regular_equity_dia_sin_sesion():
    sin_sesion = {"2026-09-21": {"is_session": False, "opens_at": None, "closes_at": None}}
    assert es_barra_regular("equity", T(2026, 9, 21, 14, 30, tzinfo=UTC), sin_sesion) is False


def test_is_regular_fallback_sin_fila_de_sesion():
    assert es_barra_regular("equity", T(2026, 9, 21, 14, 30, tzinfo=UTC), {}) is True


def test_is_regular_clases_no_nyse_siempre_true():
    for clase in ("fx", "crypto", "future", "yield", "index", "commodity"):
        assert es_barra_regular(clase, T(2026, 9, 21, 3, 0, tzinfo=UTC), {}) is True


# ---------------------------------------------------------------------------
# Agregación de barras (F4.1)
# ---------------------------------------------------------------------------

def _tick(aid, ts, close, volume=None, clase="equity"):
    return {"asset_id": aid, "timestamp_utc": ts, "close": close,
            "volume": volume, "asset_class": clase}


def test_agrupar_barras_ohlcv_y_calidad_definitive():
    # Último tick a T-10s → definitive
    ticks = [
        _tick(1, T(2026, 9, 21, 14, 30, 0, tzinfo=UTC), 100.0, 1000),
        _tick(1, T(2026, 9, 21, 14, 33, 0, tzinfo=UTC), 101.0, 3000),
        _tick(1, T(2026, 9, 21, 14, 36, 0, tzinfo=UTC), 99.5, 5000),
        _tick(1, T(2026, 9, 21, 14, 44, 50, tzinfo=UTC), 102.0, 7000),
    ]
    barras = agrupar_barras(ticks, SESION_310)
    assert len(barras) == 1
    b = barras[0]
    assert b["bar_start_utc"] == T(2026, 9, 21, 14, 30, tzinfo=UTC)
    assert b["open"] == 100.0
    assert b["high"] == 102.0
    assert b["low"] == 99.5
    assert b["close"] == 102.0
    assert b["volume_delta"] == 6000
    assert b["n_ticks"] == 4
    assert b["is_regular"] is True
    assert b["close_quality"] == "definitive"
    assert b["last_tick_offset_s"] == 10
    assert b["session_date"] == date(2026, 9, 21)


def test_agrupar_barras_cruza_frontera_de_15_min():
    ticks = [
        _tick(1, T(2026, 9, 21, 14, 44, 59, tzinfo=UTC), 100.0, 1000),
        _tick(1, T(2026, 9, 21, 14, 45, 0, tzinfo=UTC), 101.0, 2000),
        _tick(1, T(2026, 9, 21, 14, 50, 0, tzinfo=UTC), 102.0, 3000),
    ]
    barras = agrupar_barras(ticks, SESION_310)
    assert [b["bar_start_utc"] for b in barras] == [
        T(2026, 9, 21, 14, 30, tzinfo=UTC),
        T(2026, 9, 21, 14, 45, tzinfo=UTC),
    ]
    assert [b["n_ticks"] for b in barras] == [1, 2]
    assert barras[1]["open"] == 101.0 and barras[1]["close"] == 102.0
    assert barras[1]["close_quality"] == "unknown"  # último tick a T-10min


def test_agrupar_barras_sin_volumen():
    ticks = [
        _tick(1, T(2026, 9, 21, 9, 0, 0, tzinfo=UTC), 100.0, None, "crypto"),
        _tick(1, T(2026, 9, 21, 9, 14, 50, tzinfo=UTC), 101.0, None, "crypto"),
    ]
    barras = agrupar_barras(ticks, {})
    assert len(barras) == 1
    assert barras[0]["volume_delta"] is None
    assert barras[0]["is_regular"] is True


def test_agrupar_barras_sin_close():
    ticks = [_tick(1, T(2026, 9, 21, 14, 30, 0, tzinfo=UTC), None)]
    barras = agrupar_barras(ticks, SESION_310)
    assert len(barras) == 1
    assert barras[0]["open"] is None
    assert barras[0]["high"] is None
    assert barras[0]["n_ticks"] == 1


def test_agrupar_barras_por_asset_y_orden():
    ticks = [
        _tick(2, T(2026, 9, 21, 14, 40, 0, tzinfo=UTC), 10.0, 100),
        _tick(1, T(2026, 9, 21, 14, 40, 0, tzinfo=UTC), 100.0, 1000),
    ]
    barras = agrupar_barras(ticks, SESION_310)
    assert [b["asset_id"] for b in barras] == [1, 2]


def test_agrupar_barras_clase_por_defecto_equity():
    ticks = [
        {"asset_id": 1, "timestamp_utc": T(2026, 9, 21, 14, 40, 0, tzinfo=UTC),
         "close": 100.0, "volume": 1000}  # sin asset_class
    ]
    barras = agrupar_barras(ticks, SESION_310)
    # asset_class ausente → 'equity' → is_regular usa XNYS (dentro) → True
    assert barras[0]["is_regular"] is True


def test_resumen_calidad():
    barras = [
        {"close_quality": "definitive", "n_ticks": 4},
        {"close_quality": "definitive", "n_ticks": 3},
        {"close_quality": "provisional", "n_ticks": 2},
        {"close_quality": "unknown", "n_ticks": 1},
    ]
    r = resumen_calidad(barras)
    assert r["total"] == 4
    assert r["definitive"] == 2
    assert r["provisional"] == 1
    assert r["unknown"] == 1
    assert r["pct_definitive"] == 50.0
    assert r["pct_n_ticks_ge3"] == 50.0