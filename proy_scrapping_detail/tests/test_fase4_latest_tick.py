# file: proy_scrapping_detail/tests/test_fase4_latest_tick.py
"""Pruebas de la FASE 4 — F4.3 `latest_market_tick` (último tick por activo).

Cubre la proyección pura de db/latest_tick_repository.py: de una fila cruda
del scan (claves CAMPOS incl. bloques `|TF` y trazabilidad F3.3) a la fila
de `latest_market_tick` (una por activo, E-DSH-04). Sin red ni BD.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from db.latest_tick_repository import (  # noqa: E402
    _feed_delay_de,
    proyectar_latest_tick,
    upsert_latest_tick_batch,
)

UTC = timezone.utc


def _item_scan(**extra):
    item = {
        "simbolo": "NASDAQ:NVDA",
        "timestamp_utc": 1800000000,
        "fetched_at": datetime(2026, 9, 23, 20, 38, 20, tzinfo=UTC),
        "cycle_id": "a1b2c3d4-0000-4000-8000-000000000002",
        "update_mode": "delayed_streaming_900",
        "close": 228.87,
        "change": 0.10209517,
        "volume": 1000000,
        "RSI": 59.99,
        "RSI|15": 75.40,
        "CCI20|15": 94.99,
        "BBPower|15": 1.23456789,
        "ADX|15": 18.89,
        "Pivot.M.Camarilla.R3|15": 235.12345678,
    }
    item.update(extra)
    return item


def test_proyecta_fila_completa():
    fila = proyectar_latest_tick(_item_scan(), 997)
    assert fila["asset_id"] == 997
    assert fila["timestamp_utc"] == datetime.fromtimestamp(1800000000, UTC)
    # Bloque base (régimen 1D)
    assert fila["close"] == 228.87
    assert fila["change_pct"] == 0.10209517
    assert fila["volume"] == 1000000
    assert fila["rsi"] == 59.99
    # Bloque |15 (etiquetado 15m)
    assert fila["rsi_15"] == 75.40
    assert fila["cci20_15"] == 94.99
    assert fila["bbpower_15"] == 1.23456789
    assert fila["adx_15"] == 18.89
    assert fila["pivot_r3_15"] == 235.12345678
    # Trazabilidad F3.3
    assert fila["update_mode"] == "delayed_streaming_900"
    assert fila["feed_delay_s"] == 900
    assert fila["cycle_id"] is not None
    assert fila["fetched_at"] == datetime(2026, 9, 23, 20, 38, 20, tzinfo=UTC)


def test_feed_delay_de_streaming_y_delayed():
    assert _feed_delay_de('streaming') == 0
    assert _feed_delay_de('delayed_streaming_600') == 600
    assert _feed_delay_de('delayed_streaming_900') == 900
    assert _feed_delay_de(None) is None
    assert _feed_delay_de('otro') is None


def test_bloque_15_ausente_no_tumba():
    """Sin bloques |15 la fila sigue saliendo (base + trazabilidad)."""
    item = _item_scan(RSI="x")
    for clave in ("RSI|15", "CCI20|15", "BBPower|15", "ADX|15",
                  "Pivot.M.Camarilla.R3|15"):
        item.pop(clave, None)
    fila = proyectar_latest_tick(item, 7)
    assert fila is not None
    assert fila["rsi"] == "x"
    assert fila["rsi_15"] is None
    assert fila["pivot_r3_15"] is None
    assert fila["asset_id"] == 7


def test_timestamp_epoch_o_datetime_o_naive():
    f1 = proyectar_latest_tick(_item_scan(), 1)
    assert f1["timestamp_utc"] == datetime.fromtimestamp(1800000000, UTC)

    item = _item_scan(timestamp_utc=datetime(2026, 9, 22, 18, 0, tzinfo=UTC))
    assert proyectar_latest_tick(item, 1)["timestamp_utc"] == \
        datetime(2026, 9, 22, 18, 0, tzinfo=UTC)

    item = _item_scan(timestamp_utc=datetime(2026, 9, 22, 18, 0))
    assert proyectar_latest_tick(item, 1)["timestamp_utc"] == \
        datetime(2026, 9, 22, 18, 0, tzinfo=UTC)


def test_sin_timestamp_no_emite_fila():
    item = _item_scan()
    item.pop("timestamp_utc", None)
    assert proyectar_latest_tick(item, 997) is None


def test_una_fila_por_activo():
    """aunque el item se proyecte varias veces, el upsert sobrescribe la misma
    fila (PK asset_id): la API expone un dict por asset_id."""
    a = proyectar_latest_tick(_item_scan(), 42)
    b = proyectar_latest_tick(_item_scan(close=999.0), 42)
    assert a["asset_id"] == b["asset_id"] == 42
    assert b["close"] == 999.0


class _FakeDB:
    """Fake que captura la llamada a execute_values (E-RAD-16 regression)."""

    def __init__(self):
        self.query = None
        self.params = None
        self.calls = []

    def execute_values(self, query, params, template=None):
        self.calls.append((query, params, template))


def test_upsert_convierte_cycle_id_uuid_a_str():
    """Regresión E-RAD-16: si cycle_id llega como uuid.UUID (ciclo real del
    radar), el parametro debe pasarse como str — execute_values no adapta
    uuid.UUID ('can't adapt type 'UUID'')."""
    db = _FakeDB()
    cid = uuid.uuid4()
    item = _item_scan(cycle_id=cid)
    n = upsert_latest_tick_batch(db, [item], {"NASDAQ:NVDA": 997})
    assert n == 1
    assert len(db.calls) == 1
    _q, params, _t = db.calls[0]
    assert len(params) == 1
    col_cycle = params[0][13]
    assert isinstance(col_cycle, str)
    assert col_cycle == str(cid)


def test_upsert_sin_cycle_id_emmite_none():
    db = _FakeDB()
    item = _item_scan(cycle_id=None)
    assert upsert_latest_tick_batch(db, [item], {"NASDAQ:NVDA": 997}) == 1
    _q, params, _t = db.calls[0]
    assert params[0][13] is None