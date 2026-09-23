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


def parse_vector(d: List) -> Dict[str, Any]:
    """
    Parsea el vector 'd' devuelto por el scanner y extrae los campos
    mapeados según la documentación.
    Retorna un diccionario con las claves necesarias para la BD.
    """
    if not isinstance(d, list) or len(d) < 30:
        return None

    raw_class = d[0]
    share_class = raw_class[0] if isinstance(raw_class, list) and raw_class else raw_class

    return {
        "asset_class": "equity",
        "share_class": share_class,
        "daily_change_pct": d[3],
        "market_cap": d[15],
        "sector": d[22],
        "sector_es": d[23],
        "logo": d[24],
        "price_heatmap": d[25],
        "ticker": d[27],
        "company_name": d[28],
        "stream_status": d[29],
        "raw_vector": d
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
    logo_id = logo.get('logoid') if logo else None

    # Upsert con RETURNING asset_id
    # asset_class/share_class/source_discovered_by quedan con primer-gana (COALESCE).
    upsert_query = """
        INSERT INTO dim_asset (
            symbol, ticker, exchange, asset_class, share_class,
            sector, sector_es, company_name, logo_id, source_discovered_by,
            valid_from, valid_to, current_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  CURRENT_TIMESTAMP, 'infinity', TRUE)
        ON CONFLICT (symbol) DO UPDATE SET
            ticker = COALESCE(dim_asset.ticker, EXCLUDED.ticker),
            exchange = COALESCE(dim_asset.exchange, EXCLUDED.exchange),
            asset_class = COALESCE(dim_asset.asset_class, EXCLUDED.asset_class),
            share_class = COALESCE(dim_asset.share_class, EXCLUDED.share_class),
            sector = COALESCE(dim_asset.sector, EXCLUDED.sector),
            sector_es = COALESCE(dim_asset.sector_es, EXCLUDED.sector_es),
            company_name = COALESCE(dim_asset.company_name, EXCLUDED.company_name),
            logo_id = COALESCE(dim_asset.logo_id, EXCLUDED.logo_id),
            updated_at = CURRENT_TIMESTAMP
        RETURNING asset_id
    """
    result = conn.execute_query(upsert_query, (
        symbol, ticker, exchange, asset_class, share_class,
        parsed.get('sector'), parsed.get('sector_es'),
        parsed.get('company_name'), logo_id, 'heatmap'
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
            "sector_es": parsed.get('sector_es'),
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


def fetch_heatmap_data() -> Optional[List[Dict]]:
    """Obtiene el JSON del heatmap desde el endpoint de TradingView."""
    try:
        response = requests.post(
            config.HEATMAP_URL,
            headers=config.HEATMAP_HEADERS,
            timeout=config.HEATMAP_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        # La respuesta real no tiene campo 'status'
        # Verificamos que tenga 'data' y opcionalmente 'totalCount'
        if 'data' not in data:
            logger.error(f"Respuesta sin campo 'data': {data}")
            return None
            
        rows = data.get('data', [])

        # --- DEBUG temporal ---
        if rows:
            logger.info(f"DEBUG primer item: {json.dumps(rows[0], ensure_ascii=False)[:500]}")
        # --- FIN DEBUG ---

        # Validación: verificar que al menos un item traiga vector "d" no vacío
        has_vector = any(
            isinstance(it, dict) and isinstance(it.get('d'), list) and len(it['d']) > 0
            for it in rows
        )
        if not has_vector:
            # Log más detallado
            sample = rows[0] if rows else None
            logger.error(
                "El endpoint devolvió 'data' pero sin vectores 'd'. "
                "Revisar si se está enviando un payload incorrecto."
                f"Primer item: {sample}"
            )
            return None
        
        logger.info(f"Obtenidos {len(rows)} símbolos con vector completo")
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


def main():
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
            logger.info("Sin datos para insertar (probablemente mercado cerrado). "
                        "Finalizando limpiamente.")
            logger.error("No se obtuvieron datos del heatmap")
            sys.exit(1)

        inserted = process_heatmap_data(db, heatmap_data)
        logger.info(f"Procesados {inserted} registros exitosamente")

    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)
    finally:
        db.disconnect()

    logger.info("=== FIN SCRAPPER HEATMAP ===")


if __name__ == "__main__":
    main()
