# file: proy_scrapping_detail/tests/test_fase4_indicadores_tf.py
"""Pruebas de la FASE 4 — F4.2 `fact_market_indicator_tf` (formato largo).

Cubre la proyección pura de db/indicator_repository.py: de una fila cruda
del scan (claves CAMPOS incl. bloques `|TF`) a filas largas de
fact_market_indicator_tf por (asset, timestamp, tf), sin red ni BD.
"""
import os
import sys
from datetime import datetime, timezone

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from db.indicator_repository import (  # noqa: E402
    TFS_INDICADOR,
    proyectar_item,
)

UTC = timezone.utc


def _item_scan(**extra):
    item = {
        "simbolo": "NASDAQ:NVDA",
        "timestamp_utc": 1800000000,
        "close": 228.87,
        "volume": 1000000,
        "RSI": 59.99,
        "RSI|5": 70.1,
        "RSI|15": 75.40,
        "CSI|15": None,
        "CCI20|15": 94.99,
        "BBPower|15": 1.23456789,
        "ADX|15": 18.89,
        "change|15": 0.567,
        "volume|15": 4805009,
        "Pivot.M.Camarilla.R3|15": 235.12345678,
        "RSI|60": 74.57,
        "CCI20|60": 90.1,
        "BBPower|60": 2.1,
        "ADX|60": 20.5,
        "change|60": 1.2,
        "volume|60": 5500,
    }
    item.update(extra)
    return item


def test_proyecta_bloque_15():
    filas = proyectar_item(_item_scan(), 997, TFS_INDICADOR)
    f15 = [f for f in filas if f["tf"] == "15"]
    assert len(f15) == 1
    b = f15[0]
    assert b["asset_id"] == 997
    assert b["timestamp_utc"] == datetime.fromtimestamp(1800000000, UTC)
    assert b["tf"] == "15"
    assert b["rsi"] == 75.40
    assert b["cci20"] == 94.99
    assert b["bbpower"] == 1.23456789
    assert b["adx"] == 18.89
    assert b["change_pct"] == 0.567
    assert b["volume"] == 4805009
    assert b["pivot_r3"] == 235.12345678


def test_proyecta_tfs_configurados_por_defecto():
    filas = proyectar_item(_item_scan(), 997, TFS_INDICADOR)
    tfs = sorted(f["tf"] for f in filas)
    assert tfs == ["15", "5"]
    f5 = [f for f in filas if f["tf"] == "5"][0]
    # pivot solo existe en bloque |15
    assert f5["pivot_r3"] is None
    assert f5["rsi"] == 70.1


def test_tf_sin_valores_no_emite_fila():
    item = _item_scan(RSI="x")
    # quitamos todo el bloque |5 → el loop de tfs default no emite '5'
    for campo in ("RSI|5", "CCI20|5", "BBPower|5", "ADX|5", "change|5", "volume|5"):
        item.pop(campo, None)
    filas = proyectar_item(item, 997, TFS_INDICADOR)
    assert [f["tf"] for f in filas] == ["15"]


def test_item_con_ts_epoch_o_datetime():
    item = _item_scan(timestamp_utc=datetime(2026, 9, 22, 18, 0, tzinfo=UTC))
    filas = proyectar_item(item, 1, ("15",))
    assert filas[0]["timestamp_utc"] == datetime(2026, 9, 22, 18, 0, tzinfo=UTC)

    item = _item_scan(timestamp_utc=datetime(2026, 9, 22, 18, 0))
    filas = proyectar_item(item, 1, ("15",))
    assert filas[0]["timestamp_utc"] == datetime(2026, 9, 22, 18, 0, tzinfo=UTC)


def test_ts_ausente_no_emite_filas():
    item = _item_scan()
    item.pop("timestamp_utc", None)
    assert proyectar_item(item, 997, TFS_INDICADOR) == []


def test_tf_personalizado_60():
    fila = proyectar_item(_item_scan(), 997, ("60",))
    assert len(fila) == 1
    assert fila[0]["tf"] == "60"
    assert fila[0]["rsi"] == 74.57
    assert fila[0]["pivot_r3"] is None


def test_valores_vacios_no_se_pierden_en_fila():
    item = _item_scan(**{"RSI|15": None, "CCI20|15": None, "BBPower|15": None,
                         "ADX|15": None, "change|15": None, "volume|15": None})
    item["Pivot.M.Camarilla.R3|15"] = 235.0  # único valor presente del bloque 15
    filas = proyectar_item(item, 997, TFS_INDICADOR)
    f15 = [f for f in filas if f["tf"] == "15"]
    assert len(f15) == 1
    assert f15[0]["rsi"] is None
    assert f15[0]["pivot_r3"] == 235.0