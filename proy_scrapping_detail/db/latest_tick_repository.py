# file: proy_scrapping_detail/db/latest_tick_repository.py
"""F4.3 · Persistencia del último tick de mercado por activo
(`latest_market_tick`).

Cierra E-DSH-04 (M-DAT-04): una fila por activo, reescrita por UPSERT en
cada ciclo del radar. El dashboard lee ~110 filas (=== universo) para el
panel de mercado sin escanear `fact_market_series` (la historia).

Cada ciclo proyecta la marca cruda del scan (claves `CAMPOS_LIST`, incl.
bloques `|TF`) sobre la fila del activo:

- Bloque base (régimen 1D): close, change_pct, volume, rsi.
- Bloque `|15` (etiquetado 15m): rsi_15, cci20_15, bbpower_15, adx_15,
  pivot_r3_15.
- Trazabilidad (F3.3): update_mode, feed_delay_s (derivado, Test D),
  cycle_id, fetched_at.

`timestamp_utc` es el instante de captura del ciclo (también en
`fact_market_series` e `fact_market_indicator_tf` para el mismo ciclo).
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.latest_tick_repository')

# Mapeo columna <- clave del bloque base / |15 en la respuesta del scan.
_BASE = {
    "close": "close",
    "change_pct": "change",
    "volume": "volume",
    "rsi": "RSI",
}
_BLOQUE15 = {
    "rsi_15": "RSI|15",
    "cci20_15": "CCI20|15",
    "bbpower_15": "BBPower|15",
    "adx_15": "ADX|15",
}


def _feed_delay_de(update_mode) -> Optional[int]:
    """Deriva el retraso de la señal desde update_mode (Test D/F3.3)."""
    if update_mode == 'streaming':
        return 0
    if update_mode in ('delayed_streaming_600', 'delayed_streaming_900'):
        return int(update_mode.rsplit('_', 1)[1])
    return None


def proyectar_latest_tick(item: Dict, asset_id: int) -> Optional[Dict]:
    """Proyecta una fila cruda del scan a la fila de `latest_market_tick`.

    `timestamp_utc` puede venir como epoch int (scraper) o datetime.
    Retorna None si falta el símbolo/timestamp (no se puede asociar al ciclo).
    """
    ts = item.get('timestamp_utc')
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    fila = {
        "asset_id": int(asset_id),
        "timestamp_utc": ts,
        "update_mode": item.get('update_mode'),
        "cycle_id": item.get('cycle_id'),
        "fetched_at": item.get('fetched_at'),
    }
    for columna, clave in _BASE.items():
        fila[columna] = item.get(clave)
    pivot = item.get("Pivot.M.Camarilla.R3|15")
    fila["pivot_r3_15"] = pivot
    for columna, clave in _BLOQUE15.items():
        fila[columna] = item.get(clave)
    fila["feed_delay_s"] = _feed_delay_de(fila["update_mode"])
    return fila


_COLUMNAS = (
    "asset_id, timestamp_utc, close, change_pct, volume, rsi, "
    "rsi_15, cci20_15, bbpower_15, adx_15, pivot_r3_15, "
    "update_mode, feed_delay_s, cycle_id, fetched_at"
)


def upsert_latest_tick_batch(db: PostgreSQLConnector, items: List[Dict],
                             asset_cache: Dict[str, int]) -> int:
    """UPSERT de `latest_market_tick` para una lista de marcas crudas del scan.

    `asset_cache`: {symbol: asset_id} (reutiliza el del ciclo).
    ON CONFLICT (asset_id) DO UPDATE sobrescribe la fila con la marca más
    reciente del ciclo. Retorna el número de filas escritas.
    """
    if not items:
        return 0

    filas: Dict[int, Dict] = {}
    simbolos_ausentes = set()
    for item in items:
        symbol = item.get('simbolo') or item.get('symbol')
        if not symbol:
            continue
        asset_id = asset_cache.get(symbol)
        if asset_id is None:
            simbolos_ausentes.add(symbol)
            continue
        fila = proyectar_latest_tick(item, asset_id)
        if fila is not None:
            filas[asset_id] = fila

    if simbolos_ausentes:
        logger.warning(
            f"latest_market_tick: {len(simbolos_ausentes)} símbolos sin "
            "asset_id — omitidos")

    if not filas:
        logger.info("latest_market_tick: sin filas válidas para escribir")
        return 0

    query = f"""
        INSERT INTO latest_market_tick ({_COLUMNAS}) VALUES %s
        ON CONFLICT (asset_id) DO UPDATE SET
            timestamp_utc = EXCLUDED.timestamp_utc,
            close         = EXCLUDED.close,
            change_pct    = EXCLUDED.change_pct,
            volume        = EXCLUDED.volume,
            rsi           = EXCLUDED.rsi,
            rsi_15        = EXCLUDED.rsi_15,
            cci20_15      = EXCLUDED.cci20_15,
            bbpower_15    = EXCLUDED.bbpower_15,
            adx_15        = EXCLUDED.adx_15,
            pivot_r3_15   = EXCLUDED.pivot_r3_15,
            update_mode   = EXCLUDED.update_mode,
            feed_delay_s  = EXCLUDED.feed_delay_s,
            cycle_id      = EXCLUDED.cycle_id,
            fetched_at    = EXCLUDED.fetched_at,
            ingested_at   = CURRENT_TIMESTAMP
    """
    template = "(" + ", ".join(["%s"] * 15) + ")"
    params = [
        (
            f["asset_id"], f["timestamp_utc"],
            f["close"], f["change_pct"], f["volume"], f["rsi"],
            f["rsi_15"], f["cci20_15"], f["bbpower_15"], f["adx_15"],
            f["pivot_r3_15"],
            f["update_mode"], f["feed_delay_s"],
            str(f["cycle_id"]) if f["cycle_id"] is not None else None,
            f["fetched_at"],
        )
        for f in filas.values()
    ]
    db.execute_values(query, params, template=template)
    logger.info("latest_market_tick: %d filas en la tabla (una por activo)",
                len(params))
    return len(params)


def get_latest_ticks(db: PostgreSQLConnector) -> List[Dict]:
    """Fila vigente por activo (joins dim_asset), ordenada por market_cap.

    Es la lectura que evita escanear `fact_market_series` (aceptación F4.3).
    """
    query = """
        SELECT a.symbol, a.ticker, a.sector, a.asset_class,
               t.timestamp_utc, t.close, t.change_pct, t.volume, t.rsi,
               t.rsi_15, t.cci20_15, t.bbpower_15, t.adx_15, t.pivot_r3_15,
               t.update_mode, t.feed_delay_s, t.cycle_id, t.fetched_at
        FROM latest_market_tick t
        JOIN dim_asset a ON a.asset_id = t.asset_id
        WHERE a.is_active = TRUE
        ORDER BY a.symbol, t.timestamp_utc DESC NULLS LAST
    """
    return db.execute_query(query)