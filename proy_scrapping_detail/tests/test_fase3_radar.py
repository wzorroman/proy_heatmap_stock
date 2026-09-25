# file: proy_scrapping_detail/tests/test_fase3_radar.py
"""Pruebas de la FASE 3 — radar v5 (proy_scrapping_detail).

Cubre F3.1 (batch), F3.2 (CAMPOS y bloques TF), F3.3 (trazabilidad en
prepare_bd_row y feed_delay), F3.4 (prioridad + prefijos batch) y F3.12
(universo 110 -> 123). Sin red ni BD: solo funciones puras.
"""
import os
import sys

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import config  # noqa: E402
from scraper_live_tradingview_v5 import (  # noqa: E402
    CAMPOS_LIST,
    BATCH_PREFIJOS,
    PRIORIDADES,
    _bloque,
    _prioridad,
)
from datetime import datetime, timezone  # noqa: E402
from application.market_service import _feed_delay_de, prepare_bd_row  # noqa: E402


# ---------------------------------------------------------------------------
# F3.2 · CAMPOS ampliado (bloques |5, |15, |60, Pivot.M.Camarilla.R3|15)
# ---------------------------------------------------------------------------

def test_campos_incluye_bloques_de_tf():
    assert "RSI|5" in CAMPOS_LIST
    assert "RSI|15" in CAMPOS_LIST
    assert "RSI|60" in CAMPOS_LIST
    assert "ADX|60" in CAMPOS_LIST
    assert "volume|15" in CAMPOS_LIST


def test_campos_incluye_pivot_y_update_mode():
    assert "Pivot.M.Camarilla.R3|15" in CAMPOS_LIST
    assert "update_mode" in CAMPOS_LIST


def test_campos_incluye_trazabilidad_f3_3():
    for c in ("premarket_close", "premarket_change", "premarket_volume", "gap"):
        assert c in CAMPOS_LIST


def test_bloque_repeticion_de_base_1d():
    bloque = _bloque("5")
    assert bloque.count("|5") == 6  # volume, RSI, CCI20, BBPower, ADX, change


# ---------------------------------------------------------------------------
# F3.1 / F3.4 · Prefijos batch y prioridades
# ---------------------------------------------------------------------------

def test_batch_prefijos_only_america():
    assert BATCH_PREFIJOS == {"NASDAQ", "NYSE", "AMEX"}


def test_prioridad_criticos_primero():
    assert _prioridad("AMEX:SPY") == 0
    assert _prioridad("NASDAQ:QQQ") == 1
    assert _prioridad("CME_MINI:ES1!") == 9
    assert _prioridad("NASDAQ:NVDA") == 1000  # resto
    assert len(PRIORIDADES) == 10
    # F3.4: los críticos (SPY, QQQ, VIX, US10Y, DXY, NQ1!) son < 1000
    criticos = {"AMEX:SPY", "NASDAQ:QQQ", "CBOE:VX1!", "TVC:US10Y", "AMEX:UUP", "CME_MINI:NQ1!"}
    assert all(_prioridad(s) < 1000 for s in criticos)


# ---------------------------------------------------------------------------
# F3.3 · Trazabilidad + feed_delay según update_mode
# ---------------------------------------------------------------------------

def test_feed_delay_de_segun_update_mode():
    assert _feed_delay_de("streaming") == 0
    assert _feed_delay_de("delayed_streaming_600") == 600
    assert _feed_delay_de("delayed_streaming_900") == 900
    assert _feed_delay_de(None) is None
    assert _feed_delay_de("otro") is None


def test_prepare_bd_row_incluye_trazabilidad():
    fila = prepare_bd_row("NASDAQ:QQQ", {
        "simbolo": "NASDAQ:QQQ",
        "timestamp_utc": 1758600000,
        "close": 580.5,
        "volume": 12000.0,
        "rsi": 55.0,
        "cci20": 100.0,
        "bbpower": 5.0,
        "adx": 22.0,
        "change": 1.2,
        "update_mode": "delayed_streaming_900",
        "premarket_close": 581.0,
        "premarket_change": 0.8,
        "premarket_volume": 500000.0,
        "gap": 0.1,
        "fetched_at": datetime.now(timezone.utc),
    })
    assert fila["update_mode"] == "delayed_streaming_900"
    assert fila["feed_delay_s"] == 900
    assert fila["premarket_close"] == 581.0
    assert fila["gap"] == 0.1
    assert fila["fetched_at"] is not None


# ---------------------------------------------------------------------------
# F3.12 · Universo 110 -> 123
# ---------------------------------------------------------------------------

def test_universo_ampliado_a_123():
    todos = set()
    for cat in config.CONFIG_ACTIVOS.values():
        for meta in cat.values():
            todos.add(meta["primario"])
            todos.add(meta["respaldo"])
    assert len(todos) == 123
    for s in ("CME_MINI:ES1!", "AMEX:XLK", "AMEX:XLF", "AMEX:XLV", "AMEX:XLY",
              "AMEX:XLP", "AMEX:XLI", "AMEX:XLU", "AMEX:XLRE", "AMEX:XLB",
              "AMEX:XLC", "AMEX:IWM", "AMEX:RSP"):
        assert s in todos


def test_nuevos_etf_son_batch_y_es_individual():
    # F3.12: los SPDR son AMEX (batch); ES1! es CME_MINI (individual).
    for s in ("AMEX:XLK", "AMEX:IWM", "AMEX:RSP"):
        assert s.split(":")[0] in BATCH_PREFIJOS
    assert "CME_MINI:ES1!".split(":")[0] not in BATCH_PREFIJOS