# file: proy_scrapping_detail/application/market_service.py
import logging
import config
from datetime import datetime, timezone
from db.postgresql_connection import PostgreSQLConnector
from db.market_repository import insert_market_series_batch, get_asset_id_cache
from db.audit_repository import log_sync_run, update_checkpoint
from db.indicator_repository import insert_indicator_tf_batch
from db.latest_tick_repository import upsert_latest_tick_batch
from db.partitions import ensure_current_month_partition

logger = logging.getLogger('application.market_service')


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def prepare_bd_row(symbol: str, scanner_data: dict) -> dict:
    """
    Convierte la respuesta del endpoint /symbol (SHA: claves nombradas)
    en una fila para fact_market_series. raw_payload se omite (NULL, D18).

    F3.3: incorpora update_mode, cycle_id, fetched_at, feed_delay_s y
    premarket_*/gap. feed_delay_s se deriva de update_mode (Test D):
    streaming→0, delayed_streaming_600→600, delayed_streaming_900→900.

    source_checksum NO se calcula aquí: lo genera `canonical_checksum(row)`
    en `db/market_repository.py:118` (sobre el subconjunto canónico sin
    timestamp, D19) — subir cualquier cambio de esa decisión desde allí.
    """
    return {
        'symbol': symbol,
        'timestamp_utc': datetime.fromtimestamp(scanner_data['timestamp_utc'], timezone.utc),
        'close': scanner_data.get('close'),
        'volume': scanner_data.get('volume'),
        'rsi': scanner_data.get('RSI'),
        'cci20': scanner_data.get('CCI20'),
        'bbpower': scanner_data.get('BBPower'),
        'adx': scanner_data.get('ADX'),
        'pivot_camarilla_r3': scanner_data.get('Pivot.M.Camarilla.R3'),
        'perf_w': scanner_data.get('Perf.W'),
        'change_pct': scanner_data.get('change'),
        # --- F3.3 Trazabilidad temporal ---
        'update_mode': scanner_data.get('update_mode'),
        'cycle_id': scanner_data.get('cycle_id'),
        'fetched_at': scanner_data.get('fetched_at'),
        'feed_delay_s': _feed_delay_de(scanner_data.get('update_mode')),
        'premarket_close': scanner_data.get('premarket_close'),
        'premarket_change': scanner_data.get('premarket_change'),
        'premarket_volume': scanner_data.get('premarket_volume'),
        'gap': scanner_data.get('gap'),
    }


def _feed_delay_de(update_mode) -> int | None:
    """Deriva el retraso de la señal a partir del update_mode (Test D)."""
    if update_mode == 'streaming':
        return 0
    if update_mode == 'delayed_streaming_600':
        return 600
    if update_mode == 'delayed_streaming_900':
        return 900
    return None


def process_radar_batch(scanner_data: list, cycle_id=None, scanner_raw=None) -> dict:
    """
    Flujo BD: scanner data -> fact_market_series -> auditoría.
    (El CSV ya se escribió en el bucle del scraper.)
    No lanza excepciones hacia el caller: un fallo de BD no tumba el ciclo (D8).

    F4.2: `scanner_raw` (opcional) es la lista de respuestas crudas del scan
    (claves CAMPOS incl. bloques `|TF`); se proyectan a
    `fact_market_indicator_tf` con el mismo asset_id/timestamp del ciclo.
    Un fallo en esa proyección NO marca el ciclo como fallido: la serie ya
    quedó escrita y el error solo se loguea.

    F4.3: del mismo `scanner_raw` se reescribe `latest_market_tick` (una fila
    por activo, E-DSH-04). Igual salvaguarda: un fallo no tumba el ciclo.

    Retorna {'inserted': int, 'status': 'SUCCESS'|'FAILED'|'SKIPPED', 'error': str|None}.
    F3.10: distribuye el cycle_id a cada fila para trazabilidad.
    """
    run_start = now_utc()

    # 1. Verificar flag de escritura
    if not config.DB_WRITE_ENABLED:
        logger.info("Modo legacy: solo CSV, sin BD")
        return {'inserted': 0, 'status': 'SKIPPED', 'error': 'modo legacy (sin BD)'}

    # 2. Conectar a BD
    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT,
        config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
    )
    if not db.connect():
        # Sin BD no se puede escribir audit_sync_run: log local y continuar (D22).
        logger.error("BD: no se pudo conectar — se omite la escritura de este ciclo")
        return {'inserted': 0, 'status': 'FAILED', 'error': 'no se pudo conectar a BD'}

    try:
        # 3. Garantizar partición del mes actual (crea solo si falta, caso excepcional)
        ensure_current_month_partition(db, "fact_market_series")

        # 4. Distribuir cycle_id (F3.10) si no está ya puesto por el scraper
        if cycle_id:
            for fila in scanner_data:
                fila.setdefault('cycle_id', cycle_id)

        # 5. Cache de asset_id + insertar batch
        asset_cache = get_asset_id_cache(db)
        inserted = insert_market_series_batch(db, scanner_data, asset_cache=asset_cache)

        # 5b. F4.2 · Indicadores multi-TF en formato largo (mismo ciclo).
        if scanner_raw:
            try:
                insert_indicator_tf_batch(db, scanner_raw, asset_cache=asset_cache)
            except Exception as tf_error:
                # No tumba el ciclo: la serie ya está escrita (D8).
                logger.error(f"BD: fact_market_indicator_tf omitido este ciclo: {tf_error}")

        # 5c. F4.3 · Último tick por activo (E-DSH-04, dashboard sin scan).
        if scanner_raw:
            try:
                upsert_latest_tick_batch(db, scanner_raw, asset_cache=asset_cache)
            except Exception as lt_error:
                logger.error(f"BD: latest_market_tick omitido este ciclo: {lt_error}")

        # 6. Registrar auditoría (éxito)
        log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'run_start': run_start,
            'records_fetched': len(scanner_data),
            'records_upserted': inserted,
            'records_failed': len(scanner_data) - inserted,  # conteo explícito (D15)
            'status': 'SUCCESS',
            'execution_mode': 'cron',
            'source_params': {'cycle_id': str(cycle_id) if cycle_id else None}
        })

        # 7. Actualizar checkpoint BD
        update_checkpoint(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'last_timestamp': run_start,
            'records_processed': inserted,
            'status': 'ACTIVE'
        })

        return {'inserted': inserted, 'status': 'SUCCESS', 'error': None}

    except Exception as e:
        logger.error(f"BD: Error en process_radar_batch: {e}")
        # Registrar auditoría (fallo) — no propagar, el CSV ya está seguro
        try:
            log_sync_run(db, {
                'script_name': config.SCRIPT_NAME_SCRAPER,
                'run_start': run_start,
                'records_fetched': len(scanner_data),
                'records_upserted': 0,
                'records_failed': len(scanner_data),
                'status': 'FAILED',
                'error_message': str(e),
                'execution_mode': 'cron',
                'source_params': {'cycle_id': str(cycle_id) if cycle_id else None}
            })
        except Exception as audit_error:
            logger.error(f"BD: No se pudo registrar auditoría de fallo: {audit_error}")
        return {'inserted': 0, 'status': 'FAILED', 'error': str(e)}

    finally:
        db.disconnect()