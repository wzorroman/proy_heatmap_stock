# file: proy_scrapping_detail/db/sessions.py
"""F2.2 · Gate de sesión por clase de activo (M-CAP-01, E-OPS-01).

Fuente primaria del horario NYSE: dim_trading_session (poblada por
create_dim_trading_session.py). Fallback: exchange_calendars (XNYS) en
memoria si la BD no responde o falta el día.

- En el loop del radar: filtrar el símbolo, NO abortar el ciclo.
- Heatmap (solo equity/ETF): en_ventana_nyse() una sola vez por corrida.
- Calendario: en_ventana_nyse(pre_min=90) → arranque a las 08:00 ET.
"""
import functools
import logging
import os
import sys
from pathlib import Path

import pandas as pd

logger = logging.getLogger('db.sessions')

XNYS = None     # lazy
_BD_CONN = None  # lazy, singleton

PREFIJOS_CRYPTO = {"BINANCE", "BITSTAMP", "COINBASE", "KRAKEN", "OKX"}
PREFIJOS_FOREX = {"OANDA", "FX", "FX_IDC", "SAXO"}
PREFIJOS_FUTURE = {"CME", "CME_MINI", "CBOT", "NYMEX", "ICEUS", "COMEX", "NYBOT", "EUREX"}


def _get_xnys():
    global XNYS
    if XNYS is None:
        import exchange_calendars as xcals
        XNYS = xcals.get_calendar("XNYS")
    return XNYS


def _get_bd_conn():
    global _BD_CONN
    if _BD_CONN is None:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from db.postgresql_connection import PostgreSQLConnector
        _BD_CONN = PostgreSQLConnector(
            os.getenv("BD_HEATMAP_HOST", "localhost"),
            int(os.getenv("BD_HEATMAP_PORT", "5432")),
            os.getenv("BD_HEATMAP_DATABASE", "heatmap_stock"),
            os.getenv("BD_HEATMAP_USER", "postgres"),
            os.getenv("BD_HEATMAP_PASSWORD", ""),
        )
        _BD_CONN.connect()
    return _BD_CONN


@functools.lru_cache(maxsize=32)
def _sesion_desde_bd(dia_iso: str):
    """Devuelve (is_session, opens_utc, closes_utc) consultando dim_trading_session.
    (None, None, None) si no se pudo consultar (BD caída / día fuera de rango)."""
    try:
        conn = _get_bd_conn()
        rows = conn.execute_query(
            "SELECT is_session, opens_at, closes_at FROM dim_trading_session "
            "WHERE session_date = %s", (dia_iso,)
        )
        if rows and "is_session" in rows[0]:
            r = rows[0]
            return (bool(r["is_session"]), r["opens_at"], r["closes_at"])
        return (None, None, None)   # día fuera del rango poblado
    except Exception as e:
        logger.warning(f"dim_trading_session no disponible, fallback XNYS: {e}")
        return (None, None, None)


def asset_class_de(symbol: str) -> str:
    """Deriva una clase aproximada a partir del prefijo de exchange del símbolo."""
    prefijo = symbol.split(":")[0] if ":" in symbol else symbol
    if prefijo in PREFIJOS_CRYPTO:
        return "crypto"
    if prefijo in PREFIJOS_FOREX:
        return "fx"
    if prefijo in PREFIJOS_FUTURE:
        return "future"
    return "equity"


def en_ventana_nyse(pre_min: int = 30, ahora: pd.Timestamp | None = None) -> bool:
    """True si `ahora` está entre (apertura − pre_min) y el cierre de la sesión XNYS.

    Respeta feriados (Acción de Gracias, etc.) y cierres anticipados vía
    dim_trading_session / exchange_calendars. `ahora` debe ser tz-aware.
    """
    ahora = ahora or pd.Timestamp.now(tz="UTC")
    if ahora.tzinfo is None:
        ahora = ahora.tz_localize("UTC")

    dia_et = ahora.tz_convert("America/New_York").normalize().tz_localize(None)
    dia_iso = dia_et.strftime("%Y-%m-%d")

    is_session, opens_utc, closes_utc = _sesion_desde_bd(dia_iso)

    if is_session is None:
        # Fallback: calendario XNYS en memoria (no pide BD)
        cal = _get_xnys()
        if not cal.is_session(dia_et):
            return False
        abre = cal.session_open(dia_et).tz_convert("UTC").to_pydatetime()
        cierra = cal.session_close(dia_et).tz_convert("UTC").to_pydatetime()
    elif not is_session:
        return False
    else:
        abre, cierra = opens_utc, closes_utc
        if abre is None or cierra is None:
            return False

    desde = pd.Timestamp(abre) - pd.Timedelta(minutes=pre_min)
    hasta = pd.Timestamp(cierra)
    return desde <= ahora <= hasta


def en_ventana_fx(ahora: pd.Timestamp | None = None) -> bool:
    """FX opera ~24/5: cerrado en el corte de mantenimiento del fin de semana
    (aprox. viernes 22:00 UTC a domingo 22:00 UTC; ajustar al proveedor)."""
    ahora = ahora or pd.Timestamp.now(tz="UTC")
    if ahora.tzinfo is None:
        ahora = ahora.tz_localize("UTC")
    dow, hour = ahora.dayofweek, ahora.hour
    if dow == 5:                       # sábado
        return False
    if dow == 4 and hour >= 22:        # viernes desde las 22:00 UTC
        return False
    if dow == 6 and hour < 22:         # domingo antes de las 22:00 UTC
        return False
    return True


def en_ventana_cripto(ahora: pd.Timestamp | None = None) -> bool:
    return True                        # 24/7, sin gate


GATE_POR_CLASE = {
    "equity": en_ventana_nyse,
    "etf": en_ventana_nyse,
    "fx": en_ventana_fx,
    "crypto": en_ventana_cripto,
    "future": en_ventana_nyse,         # ajustar si se opera el rango nocturno CME (Q2)
}


def en_ventana(asset_class: str, **kwargs) -> bool:
    return GATE_POR_CLASE.get(asset_class, en_ventana_nyse)(**kwargs)