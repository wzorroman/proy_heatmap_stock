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
from create_partitions import create_monthly_partitions, create_partition

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


def parse_vector(d: List) -> Optional[Dict[str, Any]]:
    if not isinstance(d, list) or len(d) < 28:
        return None

    typespecs = d[0]
    share_class = ""
    if isinstance(typespecs, list) and typespecs:
        share_class = typespecs[0]
    elif isinstance(typespecs, str) and typespecs:
        share_class = typespecs

    return {
        "asset_class": "equity",
        "share_class": share_class,
        "daily_change_pct": round_value(d[1]),
        "market_cap": round_value(d[11], 2),
        "sector": d[21],
        "logo": d[22],
        "price_heatmap": round_value(d[23]),
        "ticker": d[25],
        "company_name": d[25],
        "stream_status": d[26],
        "raw_vector": [round_value(v) if isinstance(v, float) else v for v in d]
    }


def get_or_create_asset(conn: PostgreSQLConnector, symbol: str, parsed: Dict) -> int:
    """
    Obtiene o crea el asset_id en dim_asset usando INSERT ... ON CONFLICT.
    Retorna el asset_id.
    """
    ticker = parsed.get('ticker') or symbol.split(':')[-1] if ':' in symbol else symbol
    exchange = symbol.split(':')[0] if ':' in symbol else None
    asset_class = parsed.get('asset_class') or 'equity'
    share_class = parsed.get('share_class')

    logo = parsed.get('logo')
    logo_id = logo.get('logoid') if isinstance(logo, dict) else None


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


def process_heatmap_data(conn: PostgreSQLConnector, data: List[Dict]) -> int:
    """
    Procesa los datos del heatmap e inserta en la BD.
    Crea automáticamente la partición mensual si no existe.
    """
    if not data:
        logger.warning("No hay datos para procesar")
        return 0

    timestamp_utc = datetime.now(timezone.utc)
    
    total = len(data)
    logger.info(f"Preparando {total} registros para procesar...")

    # --- 1. Asegurar que la partición del mes actual existe ---
    first_day = timestamp_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (first_day + timedelta(days=32)).replace(day=1)
    partition_name = f"fact_heatmap_snapshot_{first_day.strftime('%Y_%m')}"

    if create_partition(conn, "fact_heatmap_snapshot", partition_name, first_day, next_month):
        logger.info(f"Partición {partition_name} creada exitosamente")
    else:
        logger.debug(f"Partición {partition_name} ya existe")

    # --- 2. Preparar los parámetros para la inserción ---
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

        asset_id = get_or_create_asset(conn, symbol, parsed)

        raw_metadata = {
            "asset_class": parsed.get('asset_class'),
            "share_class": parsed.get('share_class'),
            "sector": parsed.get('sector'),
            "company_name": parsed.get('company_name'),
            "logo": parsed.get('logo'),
            "ticker": parsed.get('ticker')
        }

        fact_params.append((
            asset_id,
            timestamp_utc,
            parsed.get('price_heatmap'),
            parsed.get('daily_change_pct'),
            parsed.get('market_cap'),
            parsed.get('stream_status'),
            json.dumps(parsed.get('raw_vector')),
            json.dumps(raw_metadata)
        ))

    if not fact_params:
        logger.warning("No se generaron registros para insertar")
        return 0

    logger.info(f"Preparados {len(fact_params)} registros para insertar en BD...")

    # --- 3. Inserción batch con UPSERT ---
    insert_heatmap = """
        INSERT INTO fact_heatmap_snapshot (
            asset_id, timestamp_utc, price_heatmap, daily_change_pct,
            market_cap, stream_status, raw_vector, raw_metadata
        ) VALUES %s
        ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
            price_heatmap = EXCLUDED.price_heatmap,
            daily_change_pct = EXCLUDED.daily_change_pct,
            market_cap = EXCLUDED.market_cap,
            stream_status = EXCLUDED.stream_status,
            raw_vector = EXCLUDED.raw_vector,
            raw_metadata = EXCLUDED.raw_metadata,
            ingested_at = CURRENT_TIMESTAMP
    """
    template = "(%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)"
    conn.execute_values(insert_heatmap, fact_params, template=template)
    logger.info(f"Insertados/actualizados {len(fact_params)} registros en fact_heatmap_snapshot")
    return len(fact_params)


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
    def get_market_cap(item):
        d = item.get('d', [])
        if isinstance(d, list) and len(d) > 11:
            return d[11] or 0
        return 0

    sorted_items = sorted(items, key=get_market_cap, reverse=True)
    return sorted_items[:max_symbols]


def log_sync_run(conn, script_name, run_start, records_fetched, records_upserted, status, error_message=None):
    query = """
        INSERT INTO audit_sync_run (
            script_name, run_start, run_end,
            records_fetched, records_upserted, records_failed,
            status, error_message, execution_mode
        ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, 'cron')
    """
    records_failed = records_fetched - records_upserted if records_fetched and records_upserted else 0
    conn.execute_query(query, (
        script_name, run_start,
        records_fetched, records_upserted, records_failed,
        status, error_message
    ))


def fetch_from_api() -> Optional[List[Dict]]:
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
            return None

        rows = data.get('data', [])
        has_vector = any(
            isinstance(it, dict) and isinstance(it.get('d'), list) and len(it['d']) > 0
            for it in rows
        )
        if not has_vector:
            logger.warning("API devolvió 'data' pero sin vectores 'd' (mercado cerrado?)")
            return None

        logger.info(f"API: {len(rows)} símbolos con vector completo")
        return rows

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
    return None


def fetch_heatmap_data() -> Optional[List[Dict]]:
    logger.info("Consultando API de TradingView...")
    rows = fetch_from_api()
    if rows is not None:
        filtered = filter_top_by_market_cap(rows, config.HEATMAP_MAX_SYMBOLS)
        logger.info(f"Filtrados top {len(filtered)} de {len(rows)} símbolos por market cap")
        return filtered

    logger.error("API no devolvió datos válidos")
    return None

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
        create_monthly_partitions(db, "fact_heatmap_snapshot", 1)
        heatmap_data = fetch_heatmap_data()

        if heatmap_data is None:
            log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'FAILED', 'API no devolvió datos')
            logger.error("No se obtuvieron datos del heatmap")
            sys.exit(1)

        inserted = process_heatmap_data(db, heatmap_data)
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
