# file: proy_scrapping_detail/db/market_repository.py
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.market_repository')

# Columnas que se escriben en fact_market_series (raw_payload se omite a NULL,
# D18: costo ~366 MB/mes; el crudo vive en el CSV). ingested_at usa su DEFAULT.
_COLUMNAS = (
    "asset_id, timestamp_utc, close, volume, rsi, cci20, "
    "bbpower, adx, pivot_camarilla_r3, perf_w, change_pct, source_checksum"
)


def safe_float(val: Any) -> Optional[float]:
    """Convierte a float si es posible, retorna None si no."""
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def sha256(data: str) -> str:
    """Calcula SHA-256 hex."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def canonical_checksum(row: Dict) -> str:
    """
    SHA-256 sobre el subconjunto canónico (símbolo + 9 métricas, sin timestamp).
    Estable entre capturas: detecta cambios reales de valores de mercado (D19).
    """
    canonico = {
        'symbol': row.get('symbol'),
        'close': row.get('close'),
        'volume': row.get('volume'),
        'rsi': row.get('rsi'),
        'cci20': row.get('cci20'),
        'bbpower': row.get('bbpower'),
        'adx': row.get('adx'),
        'pivot_camarilla_r3': row.get('pivot_camarilla_r3'),
        'perf_w': row.get('perf_w'),
        'change_pct': row.get('change_pct'),
    }
    return sha256(json.dumps(canonico, sort_keys=True, default=str))


def get_asset_id_cache(db: PostgreSQLConnector) -> Dict[str, int]:
    """
    Cache símbolo -> asset_id desde dim_asset (una query por ciclo).
    Solo incluye activos activos y versión vigente.
    """
    query = """
        SELECT symbol, asset_id
        FROM dim_asset
        WHERE is_active AND current_version
    """
    result = db.execute_query(query)
    cache = {}
    for row in result:
        sym = row.get('symbol')
        aid = row.get('asset_id')
        if sym is not None and aid is not None:
            cache[sym] = int(aid)
    logger.debug(f"Cache de asset_id: {len(cache)} activos")
    return cache


def insert_market_series_batch(db: PostgreSQLConnector, rows: List[Dict],
                               asset_cache: Optional[Dict[str, int]] = None) -> int:
    """
    Inserta batch de registros en fact_market_series.
    rows: List[Dict] con symbol, timestamp_utc, close, volume, rsi, cci20,
          bbpower, adx, pivot_camarilla_r3, perf_w, change_pct.

    - raw_payload se omite (NULL).
    - source_checksum se calcula sobre el subconjunto canónico sin timestamp (D19).
    - UPSERT batch ON CONFLICT (asset_id, timestamp_utc) DO UPDATE (D2).
    - Retorna número de registros insertados/actualizados.
    """
    if asset_cache is None:
        asset_cache = get_asset_id_cache(db)

    simbolos_ausentes: Set[str] = set()
    params = []
    for row in rows:
        symbol = row.get('symbol')
        if not symbol:
            continue

        asset_id = asset_cache.get(symbol)
        if asset_id is None:
            simbolos_ausentes.add(symbol)
            continue

        params.append((
            asset_id,
            row['timestamp_utc'],
            safe_float(row.get('close')),
            safe_float(row.get('volume')),
            safe_float(row.get('rsi')),
            safe_float(row.get('cci20')),
            safe_float(row.get('bbpower')),
            safe_float(row.get('adx')),
            safe_float(row.get('pivot_camarilla_r3')),
            safe_float(row.get('perf_w')),
            safe_float(row.get('change_pct')),
            canonical_checksum(row),
        ))

    if simbolos_ausentes:
        logger.warning(
            f"Símbolos no registrados en dim_asset — omitidos ({len(simbolos_ausentes)}): "
            f"{', '.join(sorted(simbolos_ausentes))}"
        )

    if not params:
        logger.info("No hay filas válidas para insertar en fact_market_series")
        return 0

    upsert_query = f"""
        INSERT INTO fact_market_series (
            {_COLUMNAS}
        ) VALUES %s
        ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            rsi = EXCLUDED.rsi,
            cci20 = EXCLUDED.cci20,
            bbpower = EXCLUDED.bbpower,
            adx = EXCLUDED.adx,
            pivot_camarilla_r3 = EXCLUDED.pivot_camarilla_r3,
            perf_w = EXCLUDED.perf_w,
            change_pct = EXCLUDED.change_pct,
            source_checksum = EXCLUDED.source_checksum,
            ingested_at = CURRENT_TIMESTAMP
    """
    template = "(" + ", ".join(["%s"] * 12) + ")"
    db.execute_values(upsert_query, params, template=template)
    logger.info(f"BD: {len(params)} registros upserted en fact_market_series")
    return len(params)