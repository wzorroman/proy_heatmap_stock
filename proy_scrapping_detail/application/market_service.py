# file: proy_scrapping_detail/application/market_service.py
import logging
import config
from datetime import datetime, timezone
from db.postgresql_connection import PostgreSQLConnector
from db.market_repository import insert_market_series_batch, get_asset_id_cache
from db.audit_repository import log_sync_run, update_checkpoint
from db.partitions import ensure_current_month_partition

logger = logging.getLogger('application.market_service')


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def prepare_bd_row(symbol: str, scanner_data: dict) -> dict:
    """
    Convierte la respuesta del endpoint /symbol (SHA: claves nombradas)
    en una fila para fact_market_series. raw_payload se omite (NULL, D18).
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
    }


def process_radar_batch(scanner_data: list) -> int:
    """
    Flujo BD: scanner data -> fact_market_series -> auditoría.
    (El CSV ya se escribió en el bucle del scraper.)
    No lanza excepciones hacia el caller: un fallo de BD no tumba el ciclo (D8).
    """
    run_start = now_utc()

    # 1. Verificar flag de escritura
    if not config.DB_WRITE_ENABLED:
        logger.info("Modo legacy: solo CSV, sin BD")
        return 0

    # 2. Conectar a BD
    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT,
        config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
    )
    if not db.connect():
        # Sin BD no se puede escribir audit_sync_run: log local y continuar (D22).
        logger.error("BD: no se pudo conectar — se omite la escritura de este ciclo")
        return 0

    try:
        # 3. Garantizar partición del mes actual (crea solo si falta, caso excepcional)
        ensure_current_month_partition(db, "fact_market_series")

        # 4. Cache de asset_id + insertar batch
        asset_cache = get_asset_id_cache(db)
        inserted = insert_market_series_batch(db, scanner_data, asset_cache=asset_cache)

        # 5. Registrar auditoría (éxito)
        log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'run_start': run_start,
            'records_fetched': len(scanner_data),
            'records_upserted': inserted,
            'records_failed': len(scanner_data) - inserted,  # conteo explícito (D15)
            'status': 'SUCCESS',
            'execution_mode': 'cron'
        })

        # 6. Actualizar checkpoint BD
        update_checkpoint(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'last_timestamp': run_start,
            'records_processed': inserted,
            'status': 'ACTIVE'
        })

        return inserted

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
                'execution_mode': 'cron'
            })
        except Exception as audit_error:
            logger.error(f"BD: No se pudo registrar auditoría de fallo: {audit_error}")
        return 0

    finally:
        db.disconnect()