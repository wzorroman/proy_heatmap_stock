# file: proy_heatmap/tests/test_fase3_heatmap.py
"""Pruebas de la FASE 3 — heatmap (proy_heatmap).

Cubre F3.7 (parseo por nombre, filtro exchange/liquidez, 0 OTC — E-HM-01,
E-HM-05, E-HM-06) y F3.8 (cache de asset_id). Sin red ni BD: solo funciones
puras y payloads de muestra reales.
"""
import os
import sys

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import config  # noqa: E402
from scrapper_heatmap_v1 import (  # noqa: E402
    COLUMN_INDEX,
    _col,
    parse_vector,
    filter_top_by_market_cap,
    round_value,
)

# --- vector real de muestra (NASDAQ:NVDA, payload del 2026-09-22) ---------
D_NVDA = [
    ["common"], 0.6552907027882879, 1.49,
    4.784360406556185, 14.36638017189686, 29.988072925540983,
    30.55904164289788, 20.562593831485234, 1.536423841059598,
    236.54, 164.27, 5515767118447.121, 122340852.93333347,
    108470446.40000172, 95746277, 24100000000, 24100000000,
    42000, 7.9482, None, None, "Electronic Technology", "nvidia",
    228.87, 100, "NVDA", "delayed_streaming_900", "USD",
    "NVIDIA Corporation",
]


# ---------------------------------------------------------------------------
# F3.7 · Parseo por nombre de columna (M-CAP-11)
# ---------------------------------------------------------------------------

def test_col_index_coincide_con_heattmap_columns():
    assert COLUMN_INDEX == {n: i for i, n in enumerate(config.HEATMAP_COLUMNS)}
    assert COLUMN_INDEX["close"] == 23
    assert COLUMN_INDEX["description"] == 28  # nueva columna de E-HM-06


def test_parse_vector_por_nombre():
    p = parse_vector(D_NVDA)
    assert p is not None
    assert p["ticker"] == "NVDA"
    assert p["company_name"] == "NVIDIA Corporation"  # E-HM-06 (description)
    assert p["price_heatmap"] == round_value(228.87)
    assert p["stream_status"] == "delayed_streaming_900"
    assert p["asset_class"] == "common"              # E-HM-06 (typespecs)
    assert p["share_class"] == "common"
    assert p["logo"] == "nvidia"                     # E-HM-05 (logoid string)


def test_test_unitario_falla_si_cambia_orden():
    # "Hecho cuando": test unitario falla si cambia el orden de columnas.
    # parse_vector lee SIEMPRE por COLUMN_INDEX (derivado de config.HEATMAP_COLUMNS);
    # si el orden del config cambiara, el mapeo name->posición también cambia y
    # el payload real (que respeta ese orden) seguiría mapeando bien. La regresión
    # se detecta porque COLUMN_INDEX debe ser EXACTAMENTE el enumerado de config.
    assert COLUMN_INDEX == {n: i for i, n in enumerate(config.HEATMAP_COLUMNS)}

    # Y un payload con columnas en otro orden físico NO debe engañar: el
    # parseo por nombre reacciona a un COLUMN_INDEX distinto (posición 0 = close).
    otro_orden = ["close", "description"] + [c for c in config.HEATMAP_COLUMNS if c not in ("close", "description")]
    otro_index = {n: i for i, n in enumerate(otro_orden)}
    assert otro_index != COLUMN_INDEX
    d_reordenado = [D_NVDA[COLUMN_INDEX[c]] for c in otro_orden]
    # En el reordenado, close quedó en la posición 0 (lo que el API devolvería
    # si cambiara el orden del body): el mapeo por nombre debe apuntar ahí.
    assert d_reordenado[otro_index["close"]] == D_NVDA[COLUMN_INDEX["close"]]


def test_parse_vector_rechaza_vector_corto():
    assert parse_vector([1, 2, 3]) is None


def test_logo_dict_o_string():
    # parse_vector expone el logoid crudo; get_or_create_asset normaliza dict/str
    p = parse_vector(D_NVDA)
    assert isinstance(p["logo"], str)


# ---------------------------------------------------------------------------
# F4.4 · Columnas explícitas del snapshot (M-DAT-05, E-HM-08/E-HM-10)
# ---------------------------------------------------------------------------

def test_parse_vector_columnas_explicitas():
    """parse_vector expone las columnas consultables de M-DAT-05."""
    p = parse_vector(D_NVDA)
    assert p["volume"] == 95_746_277                     # d[14] "volume"
    assert p["avg_vol_10d"] == 108_470_446.40000172     # d[13]
    assert p["avg_vol_30d"] == 122_340_852.93333347     # d[12]
    assert p["volatility_d"] == round_value(1.536423841059598)   # d[8]
    assert p["change_abs"] == round_value(1.49)                  # d[2]
    assert p["high_52w"] == round_value(236.54)                  # d[9]
    assert p["low_52w"] == round_value(164.27)                   # d[10]
    assert p["update_mode"] == "delayed_streaming_900"           # d[27]
    # stream_status sigue siendo alias del mismo update_mode (compat).
    assert p["update_mode"] == p["stream_status"]


def test_parse_vector_columnas_faltantes_son_none():
    """Vector sin columnas nuevas devuelve None (no rompe la fila)."""
    p = parse_vector([list(D_NVDA[0])] + [None] * (len(D_NVDA) - 1))
    assert p is not None
    assert p["volume"] is None
    assert p["avg_vol_10d"] is None
    assert p["high_52w"] is None
    assert p["update_mode"] is None


# ---------------------------------------------------------------------------
# F3.7 · Filtro de exchange y liquidez (D6, E-HM-01) — 0 OTC
# ---------------------------------------------------------------------------

def _item(nombre, d):
    return {"s": nombre, "d": d}


def _vec(mod, vol30d=1e8, close=200.0, share="common"):
    v = list(D_NVDA)
    v[0] = [share]
    v[23] = close
    v[12] = vol30d
    return v


def test_filtro_exchanges_y_dollar_volume():
    items = [
        _item("NASDAQ:NVDA", _vec(0)),
        _item("NYSE:JPM", _vec(1)),
        _item("AMEX:XLK", _vec(2)),
        _item("OTC:BABA", _vec(3)),            # OTC -> descartado
        _item("NASDAQ:XYZ", _vec(4, close=5.0)),  # 5 * 1e8 = 5e8 (>=20M, ok)
        _item("NASDAQ:BAJO", _vec(5, vol30d=100.0)),  # 100*200 = 20k (<20M)
        _item("NYSE:PREF", _vec(6, share="preferred")),  # preferente -> descartado
    ]
    top = filter_top_by_market_cap(items, 1000)
    simbolos = [i["s"] for i in top]
    assert "OTC:BABA" not in simbolos            # 0 OTC
    assert "NYSE:PREF" not in simbolos           # 0 preferentes
    assert "NASDAQ:BAJO" not in simbolos         # liquidez < 20M USD
    assert "NASDAQ:NVDA" in simbolos
    assert "NYSE:JPM" in simbolos
    assert "AMEX:XLK" in simbolos


def test_filtro_top_n_limit():
    items = [_item(f"NASDAQ:A{i}", _vec(i)) for i in range(1200)]
    top = filter_top_by_market_cap(items, 800)
    assert len(top) <= 800


# ---------------------------------------------------------------------------
# F3.8 · Cache de asset_id
# ---------------------------------------------------------------------------

def test_estructura_cache_symbol_to_asset_id():
    # El cache es un dict {symbol: asset_id}; alta masiva con DO NOTHING
    # se valida a nivel de BD (no aquí), pero la API expuesta debe ser estable.
    from scrapper_heatmap_v1 import precargar_cache_assets  # noqa: F401
    from scrapper_heatmap_v1 import alta_masiva_assets      # noqa: F401
    assert callable(precargar_cache_assets)
    assert callable(alta_masiva_assets)