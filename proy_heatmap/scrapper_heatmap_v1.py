#!/usr/bin/env python3
"""
SCRAPER HEATMAP - VERSIÓN DIRECTO A BD
=======================================
Script: scrapper_heatmap.py
Descripción: Obtiene el snapshot del heatmap de TradingView
             y lo guarda directamente en PostgreSQL (fact_heatmap_snapshot).

Uso:
    python scrapper_heatmap.py

Dependencias:
    - requests
    - psycopg2-binary
    - python-dotenv
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from create_partitions import create_monthly_partitions

# Asegurar que el path del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.config_logging import get_logger
from db.postgresql_connection import PostgreSQLConnector

logger = get_logger('scrapper_heatmap')


def round_value(value, decimals=4):
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return value


# F3.7 / M-CAP-11: parseo por NOMBRE (índice→columna desde config.HEATMAP_COLUMNS).
# El test unitario falla si cambia el orden de columnas.
COLUMN_INDEX = {name: i for i, name in enumerate(config.HEATMAP_COLUMNS)}


def _col(d: List, name: str):
    """Valor de columna por nombre usando COLUMN_INDEX (parseo por nombre)."""
    idx = COLUMN_INDEX.get(name)
    if idx is None or not isinstance(d, list) or idx >= len(d):
        return None
    return d[idx]


def parse_vector(d: List) -> Optional[Dict[str, Any]]:
    if not isinstance(d, list) or len(d) < len(config.HEATMAP_COLUMNS):
        return None

    # E-HM-06 / M-CAP-11: asset_class y share_class desde typespecs.
    typespecs = _col(d, "typespecs")
    share_class = ""
    if isinstance(typespecs, list) and typespecs:
        share_class = typespecs[0]
    elif isinstance(typespecs, str) and typespecs:
        share_class = typespecs

    return {
        "asset_class": share_class or "equity",
        "share_class": share_class,
        "daily_change_pct": round_value(_col(d, "change")),
        "market_cap": round_value(_col(d, "market_cap_basic"), 2),
        "sector": _col(d, "sector"),
        "logo": _col(d, "logoid"),
        "price_heatmap": round_value(_col(d, "close")),
        "ticker": _col(d, "name"),
        "company_name": _col(d, "description") or _col(d, "name"),
        "stream_status": _col(d, "update_mode"),
        # F4.4 / M-DAT-05: columnas explícitas (E-HM-08/E-HM-10). raw_vector
        # se conserva pero deja de ser la fuente principal de lectura.
        "volume": _col(d, "volume"),
        "avg_vol_10d": _col(d, "average_volume_10d_calc"),
        "avg_vol_30d": _col(d, "average_volume_30d_calc"),
        "volatility_d": round_value(_col(d, "Volatility.D")),
        "change_abs": round_value(_col(d, "change_abs")),
        "high_52w": round_value(_col(d, "price_52_week_high")),
        "low_52w": round_value(_col(d, "price_52_week_low")),
        "update_mode": _col(d, "update_mode"),
        "dollar_volume_30d": round_value(_col(d, "average_volume_30d_calc") * _col(d, "close"), 2)
        if _col(d, "average_volume_30d_calc") and _col(d, "close") else None,
        "raw_vector": [round_value(v) if isinstance(v, float) else v for v in d]
    }


def get_or_create_asset(conn: PostgreSQLConnector, symbol: str, parsed: Dict) -> int:
    """
    Obtiene o crea el asset_id en dim_asset usando INSERT ... ON CONFLICT.
    Retorna el asset_id.
    """
    ticker = parsed.get('ticker') or (symbol.split(':')[-1] if ':' in symbol else symbol)
    exchange = symbol.split(':')[0] if ':' in symbol else None
    asset_class = parsed.get('asset_class') or 'equity'
    share_class = parsed.get('share_class')

    # E-HM-05: logoid llega como string ("nvidia"), no dict.
    logo_id = parsed.get('logo')
    if isinstance(logo_id, dict):
        logo_id = logo_id.get('logoid')
    if not isinstance(logo_id, str) or not logo_id.strip():
        logo_id = None

    # Upsert con RETURNING asset_id
    # asset_class/share_class/source_discovered_by quedan con primer-gana (COALESCE).
    upsert_query = """
        INSERT INTO dim_asset (
            symbol, ticker, exchange, asset_class, share_class,
            sector, company_name, logo_id, source_discovered_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET
            ticker = COALESCE(dim_asset.ticker, EXCLUDED.ticker),
            exchange = COALESCE(dim_asset.exchange, EXCLUDED.exchange),
            asset_class = COALESCE(dim_asset.asset_class, EXCLUDED.asset_class),
            share_class = COALESCE(dim_asset.share_class, EXCLUDED.share_class),
            sector = COALESCE(dim_asset.sector, EXCLUDED.sector),
            company_name = COALESCE(dim_asset.company_name, EXCLUDED.company_name),
            logo_id = COALESCE(dim_asset.logo_id, EXCLUDED.logo_id),
            updated_at = CURRENT_TIMESTAMP
        RETURNING asset_id
    """
    result = conn.execute_query(upsert_query, (
        symbol, ticker, exchange, asset_class, share_class,
        parsed.get('sector'), parsed.get('company_name'), logo_id, 'heatmap'
    ))
    if result and 'asset_id' in result[0]:
        return result[0]['asset_id']
    raise RuntimeError(f"No se pudo obtener/crear asset_id para {symbol}")


def precargar_cache_assets(conn: PostgreSQLConnector) -> Dict[str, int]:
    """F3.8: cache symbol→asset_id (activos vigentes). 1 sentencia SELECT."""
    cache: Dict[str, int] = {}
    rows = conn.execute_query(
        "SELECT asset_id, symbol FROM dim_asset WHERE is_active"
    )
    for r in rows or []:
        cache[r['symbol']] = r['asset_id']
    logger.info(f"F3.8: cache de assets precargado ({len(cache)} símbolos)")
    return cache


def alta_masiva_assets(conn: PostgreSQLConnector, pendientes: Dict[str, Dict]) -> Dict[str, int]:
    """F3.8: alta masiva de activos nuevos con DO NOTHING (1 sentencia).

    Retorna dict symbol→asset_id para los incógnitos recién creados.
    """
    if not pendientes:
        return {}
    insert_query = """
        INSERT INTO dim_asset (
            symbol, ticker, exchange, asset_class, share_class,
            sector, company_name, logo_id, source_discovered_by
        ) VALUES %s
        ON CONFLICT (symbol) DO NOTHING
        RETURNING asset_id, symbol
    """
    rows = []
    import itertools

    def chunks(seq, n=500):
        it = iter(seq)
        while True:
            c = list(itertools.islice(it, n))
            if not c:
                return
            yield c

    nuevos: Dict[str, int] = {}
    for lote in chunks(list(pendientes.items()), 500):
        params = []
        for symbol, parsed in lote:
            ticker = parsed.get('ticker') or (symbol.split(':')[-1] if ':' in symbol else symbol)
            exchange = symbol.split(':')[0] if ':' in symbol else None
            asset_class = parsed.get('asset_class') or 'equity'
            share_class = parsed.get('share_class')
            logo_id = parsed.get('logo')
            if isinstance(logo_id, dict):
                logo_id = logo_id.get('logoid')
            if not isinstance(logo_id, str) or not logo_id.strip():
                logo_id = None
            params.append((
                symbol, ticker, exchange, asset_class, share_class,
                parsed.get('sector'), parsed.get('company_name'), logo_id, 'heatmap'
            ))
        template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        result = conn.execute_values(insert_query, params, template=template)
        for r in result or []:
            nuevos[r['symbol']] = r['asset_id']
    if nuevos:
        logger.info(f"F3.8: alta masiva DO NOTHING: {len(nuevos)} activos nuevos")
    else:
        logger.info("F3.8: alta masiva DO NOTHING: sin activos nuevos")
    return nuevos


def process_heatmap_data(conn: PostgreSQLConnector, data: List[Dict], cache_assets: Optional[Dict[str, int]] = None, fetched_at: Optional[datetime] = None) -> int:
    """
    Procesa los datos del heatmap e inserta en la BD.
    Crea automáticamente la partición mensual si no existe.

    F3.8: usa cache de asset_id (≤ 3 sentencias SQL de dimensión por snapshot):
      1) SELECT precarga cache, 2) INSERT masivo DO NOTHING de nuevos, 3) SELECT reconciliación.

    F4.4 (M-DAT-05): escribe las columnas explícitas del vector d
    (volume, avg_vol_10d/30d, volatility_d, change_abs, high/low 52w,
    update_mode) y `fetched_at` (E-HM-10: instante real del fetch).
    `timestamp_utc` sigue siendo la hora de escritura del ciclo.
    """
    if not data:
        logger.warning("No hay datos para procesar")
        return 0

    timestamp_utc = datetime.now(timezone.utc)
    if fetched_at is None:
        fetched_at = timestamp_utc
    
    total = len(data)
    logger.info(f"Preparando {total} registros para procesar...")

    # --- Creación de partición excluida aquí (E-HM-11): única ruta en main() ---

    # --- 1. Cache de assets (F3.8): precargar + preparar parsed por símbolo ---
    if cache_assets is None:
        cache_assets = {}
    incognitos: Dict[str, Dict] = {}
    fact_params = []
    for idx, item in enumerate(data, 1):
        if idx % 1000 == 0:
            logger.info(f"Procesando registro {idx}/{total}...")

        symbol = item.get('s')
        if not symbol:
            continue
        d = item.get('d')
        if not isinstance(d, list):
            logger.warning(f"Vector d inválido para {symbol}")
            continue

        parsed = parse_vector(d)
        if parsed is None:
            logger.warning(f"Vector incompleto para {symbol} (len={len(d) if isinstance(d, list) else 'N/A'})")
            continue

        # Junta en cache si no está presente
        if symbol not in cache_assets:
            incognitos[symbol] = parsed
        else:
            fact_params.append((symbol, parsed))

    # Si hay símbolos sin asset_id: alta masiva con DO NOTHING (F3.8)
    if incognitos:
        nuevos = alta_masiva_assets(conn, incognitos)
        cache_assets.update(nuevos)
        # Reconciliación F3.8: símbolos que tienen cache pero no aparecieron (colisión)
        sin_resolver = [s for s in incognitos if s not in cache_assets]
        if sin_resolver:
            logger.warning(f"F3.8: {len(sin_resolver)} símbolos sin resolución, consulta puntual")
            placeholders = ",".join(["%s"] * len(sin_resolver))
            rows = conn.execute_query(
                f"SELECT asset_id, symbol FROM dim_asset WHERE symbol IN ({placeholders})",
                tuple(sin_resolver)
            )
            for r in rows or []:
                cache_assets[r['symbol']] = r['asset_id']
        for symbol, parsed in incognitos.items():
            if symbol in cache_assets:
                fact_params.append((symbol, parsed))

    # --- 2. Preparar params de hecho ---
    final_params = []
    for symbol, parsed in fact_params:
        asset_id = cache_assets[symbol]

        raw_metadata = {
            "asset_class": parsed.get('asset_class'),
            "share_class": parsed.get('share_class'),
            "sector": parsed.get('sector'),
            "company_name": parsed.get('company_name'),
            "logo": parsed.get('logo'),
            "ticker": parsed.get('ticker')
        }

        final_params.append((
            asset_id,
            timestamp_utc,
            parsed.get('price_heatmap'),
            parsed.get('daily_change_pct'),
            parsed.get('market_cap'),
            parsed.get('stream_status'),
            json.dumps(parsed.get('raw_vector')),
            json.dumps(raw_metadata),
            # --- F4.4 / M-DAT-05: columnas explícitas + fetched_at (E-HM-10) ---
            parsed.get('volume'),
            parsed.get('avg_vol_10d'),
            parsed.get('avg_vol_30d'),
            parsed.get('volatility_d'),
            parsed.get('change_abs'),
            parsed.get('high_52w'),
            parsed.get('low_52w'),
            parsed.get('update_mode'),
            fetched_at,
        ))

    if not final_params:
        logger.warning("No se generaron registros para insertar")
        return 0

    logger.info(f"Preparados {len(final_params)} registros para insertar en BD...")

    # --- 3. Inserción batch con UPSERT ---
    insert_heatmap = """
        INSERT INTO fact_heatmap_snapshot (
            asset_id, timestamp_utc, price_heatmap, daily_change_pct,
            market_cap, stream_status, raw_vector, raw_metadata,
            volume, avg_vol_10d, avg_vol_30d, volatility_d, change_abs,
            high_52w, low_52w, update_mode, fetched_at
        ) VALUES %s
        ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
            price_heatmap = EXCLUDED.price_heatmap,
            daily_change_pct = EXCLUDED.daily_change_pct,
            market_cap = EXCLUDED.market_cap,
            stream_status = EXCLUDED.stream_status,
            raw_vector = EXCLUDED.raw_vector,
            raw_metadata = EXCLUDED.raw_metadata,
            volume = EXCLUDED.volume,
            avg_vol_10d = EXCLUDED.avg_vol_10d,
            avg_vol_30d = EXCLUDED.avg_vol_30d,
            volatility_d = EXCLUDED.volatility_d,
            change_abs = EXCLUDED.change_abs,
            high_52w = EXCLUDED.high_52w,
            low_52w = EXCLUDED.low_52w,
            update_mode = EXCLUDED.update_mode,
            fetched_at = EXCLUDED.fetched_at,
            ingested_at = CURRENT_TIMESTAMP
    """
    template = "(" + ", ".join(["%s"] * 17) + ")"
    conn.execute_values(insert_heatmap, final_params, template=template)
    logger.info(f"Insertados/actualizados {len(final_params)} registros en fact_heatmap_snapshot")
    return len(final_params)


# # --- Fallback (deshabilitado) ---
# def load_fallback_data() -> Optional[List[Dict]]:
#     """
#     Carga el payload desde un archivo de respaldo.
#     Acepta dos formatos:
#       - JSON con estructura {"data": [{"s": ..., "d": [...]}]}
#       - CSV con columnas: symbol, raw_d_json, raw_d_len, exported_at_utc
#     """
#     path = config.HEATMAP_FALLBACK_PATH
#     if not os.path.isabs(path):
#         project_root = os.path.dirname(os.path.abspath(__file__))
#         path = os.path.join(project_root, path)
#
#     if not os.path.exists(path):
#         logger.error(f"Archivo de fallback no encontrado: {path}")
#         return None
#
#     ext = os.path.splitext(path)[1].lower()
#     try:
#         if ext == '.json':
#             with open(path, 'r', encoding='utf-8') as f:
#                 payload = json.load(f)
#             rows = payload.get('data', []) if isinstance(payload, dict) else []
#         elif ext == '.csv':
#             rows = _load_fallback_from_csv(path)
#         else:
#             logger.error(f"Extension de fallback no soportada: {ext}")
#             return None
#     except Exception as e:
#         logger.error(f"Error al leer archivo de fallback: {e}")
#         return None
#
#     if not rows:
#         logger.error("Fallback sin registros validos")
#         return None
#
#     has_vector = any(
#         isinstance(it, dict) and isinstance(it.get('d'), list) and len(it['d']) > 0
#         for it in rows
#     )
#     if not has_vector:
#         logger.error("Fallback sin vectores 'd' validos")
#         return None
#
#     logger.info(f"Fallback cargado: {len(rows)} simbolos desde {os.path.basename(path)}")
#     return rows
#
#
# def _load_fallback_from_csv(path: str) -> List[Dict]:
#     """
#     Reconstruye la lista de items {s, d} a partir de un CSV con columnas
#     'symbol' y 'raw_d_json' (vector d serializado como JSON).
#     """
#     import csv
#     rows: List[Dict] = []
#     with open(path, 'r', encoding='utf-8', newline='') as f:
#         reader = csv.DictReader(f)
#         for rec in reader:
#             symbol = (rec.get('symbol') or '').strip()
#             raw_d = (rec.get('raw_d_json') or '').strip()
#             if not symbol or not raw_d:
#                 continue
#             try:
#                 d = json.loads(raw_d)
#             except json.JSONDecodeError as e:
#                 logger.warning(f"JSON invalido en {symbol}: {e}")
#                 continue
#             if isinstance(d, list) and d:
#                 rows.append({"s": symbol, "d": d})
#     return rows


def filter_top_by_market_cap(items: List[Dict], max_symbols: int) -> List[Dict]:
    """
    F3.7 / D6: universo del heatmap = NASDAQ/NYSE/AMEX, acciones comunes,
    volumen en USD >= 20 M, top-N por market cap (N 600-800).
    Filtra OTC y preferentes/unidades (E-HM-01).
    """
    EXCHANGES = config.HEATMAP_ALLOWED_EXCHANGES
    MIN_USD = config.HEATMAP_MIN_USD_VOL

    def get_market_cap(item):
        return _col(item.get('d', []), "market_cap_basic") or 0

    def es_admisible(item) -> bool:
        symbol = item.get('s') or ''
        if ':' not in symbol:
            return False
        exchange = symbol.split(':', 1)[0]
        if exchange not in EXCHANGES:
            return False
        d = item.get('d', [])
        if not isinstance(d, list) or len(d) < len(config.HEATMAP_COLUMNS):
            return False
        # D6: acciones comunes (no preferred/unit); typespecs[0]
        typespecs = _col(d, "typespecs")
        share = typespecs[0] if isinstance(typespecs, list) and typespecs else typespecs
        if share and share not in ('common', ''):
            return False
        # D6: volumen USD = average_volume_30d * close >= 20M
        avg_vol = _col(d, "average_volume_30d_calc")
        close = _col(d, "close")
        if isinstance(avg_vol, (int, float)) and isinstance(close, (int, float)):
            dollar_vol = avg_vol * close
        else:
            dollar_vol = 0
        return dollar_vol >= MIN_USD

    admisibles = [item for item in items if es_admisible(item)]
    total_org = len(items)
    descartados = total_org - len(admisibles)
    if descartados:
        logger.info(f"F3.7: descartados {descartados}/{total_org} (OTC/preferred/unit o liquidez < 20M USD)")

    sorted_items = sorted(admisibles, key=get_market_cap, reverse=True)
    return sorted_items[:max_symbols]


def log_sync_run(conn, script_name, run_start, records_fetched, records_upserted, status, error_message=None):
    query = """
        INSERT INTO audit_sync_run (
            script_name, run_start, run_end,
            records_fetched, records_upserted, records_failed,
            status, error_message, execution_mode
        ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, 'cron')
    """
    records_failed = max((records_fetched or 0) - (records_upserted or 0), 0)
    conn.execute_query(query, (
        script_name, run_start,
        records_fetched, records_upserted, records_failed,
        status, error_message
    ))


def fetch_from_api() -> tuple:
    """
    Retorna (estado, rows | None) donde estado ∈ {'ok', 'closed', 'error'}.
    - 'ok': rows con vectores 'd' válidos.
    - 'closed': API respondió 'data' pero sin vectores (mercado cerrado/fuera de sesión).
    - 'error': fallo real de red/HTTP/JSON.
    """
    try:
        response = requests.post(
            config.HEATMAP_URL,
            headers=config.HEATMAP_HEADERS,
            json=config.HEATMAP_BODY,
            timeout=config.HEATMAP_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if 'data' not in data:
            logger.error("Respuesta del API sin campo 'data'")
            return 'error', None

        rows = data.get('data', [])
        has_vector = any(
            isinstance(it, dict) and isinstance(it.get('d'), list) and len(it['d']) > 0
            for it in rows
        )
        if not has_vector:
            logger.warning("API devolvió 'data' pero sin vectores 'd' (mercado cerrado?)")
            return 'closed', None

        logger.info(f"API: {len(rows)} símbolos con vector completo")
        return 'ok', rows

    except requests.exceptions.Timeout:
        logger.error("Timeout al conectar con TradingView")
    except requests.exceptions.ConnectionError:
        logger.error("Error de conexión a TradingView")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except ValueError as e:
        logger.error(f"Error al parsear JSON: {e}")
    except Exception as e:
        logger.error(f"Error al obtener datos del heatmap: {e}")
    return 'error', None


def fetch_heatmap_data() -> tuple:
    logger.info("Consultando API de TradingView...")
    # F4.4 / E-HM-10: fetched_at es EL instante del fetch (no el de escritura).
    fetched_at = datetime.now(timezone.utc)
    estado, rows = fetch_from_api()
    if estado == 'ok' and rows is not None:
        filtered = filter_top_by_market_cap(rows, config.HEATMAP_MAX_SYMBOLS)
        logger.info(f"Filtrados top {len(filtered)} de {len(rows)} símbolos por market cap")
        return 'ok', filtered, fetched_at

    return estado, None, fetched_at

def main():
    run_start = datetime.now(timezone.utc)
    logger.info("=== INICIO SCRAPPER HEATMAP ===")

    db = PostgreSQLConnector(
        host=config.PG_HOST,
        port=config.PG_PORT,
        database=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD
    )
    if not db.connect():
        logger.error("No se pudo conectar a PostgreSQL. Abortando.")
        sys.exit(1)

    try:
        # Gate NYSE único (F2.2, M-CAP-01): equity/ETF solo en ventana.
        from db.sessions import en_ventana_nyse
        if not en_ventana_nyse(db):
            log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'SKIPPED',
                         'fuera de la ventana NYSE (dim_trading_session)')
            logger.info("Fuera de la ventana NYSE: se omite el ciclo (SKIPPED)")
            sys.exit(0)

        # Orden F1.3: fetch → validar → DDL → procesar (E-HM-16)
        estado, heatmap_data, fetched_at = fetch_heatmap_data()

        if estado == 'closed':
            log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'SKIPPED',
                         'API sin vectores: mercado cerrado o fuera de sesión')
            logger.info("Mercado cerrado: se omite el ciclo (SKIPPED)")
            sys.exit(0)

        if estado == 'error' or heatmap_data is None:
            log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'FAILED', 'API no devolvió datos')
            logger.error("Error al obtener datos del heatmap")
            sys.exit(1)

        # DDL: única ruta (E-HM-11) — tras validar la API
        create_monthly_partitions(db, "fact_heatmap_snapshot", 1)

        # F3.8: cache de asset_id precargado (reutilizado por process_heatmap_data)
        cache_assets = precargar_cache_assets(db)

        inserted = process_heatmap_data(db, heatmap_data, cache_assets=cache_assets,
                                        fetched_at=fetched_at)
        log_sync_run(db, 'scrapper_heatmap_v1', run_start, len(heatmap_data), inserted, 'SUCCESS')
        logger.info(f"Procesados {inserted} registros exitosamente")

    except Exception as e:
        log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'FAILED', str(e))
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)
    finally:
        db.disconnect()

    logger.info("=== FIN SCRAPPER HEATMAP ===")


if __name__ == "__main__":
    main()
