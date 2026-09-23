# file: proy_scrapping_detail/application/event_service.py
import logging
import config
from datetime import datetime, timezone
from db.postgresql_connection import PostgreSQLConnector
from db.event_repository import insert_events_batch
from db.audit_repository import log_sync_run, update_checkpoint

logger = logging.getLogger('application.event_service')


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def process_calendar_batch(eventos_raw: list) -> int:
    """
    Flujo BD: eventos crudos -> fact_economic_event -> auditoría.
    (El CSV y el checkpoint local ya se guardaron antes de llamar.)
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
        logger.error("BD: no se pudo conectar — se omite la escritura de este ciclo")
        return 0

    try:
        # 3. Escribir eventos en BD
        inserted = insert_events_batch(db, eventos_raw)

        # 4. Registrar auditoría (éxito)
        log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'run_start': run_start,
            'records_fetched': len(eventos_raw),
            'records_upserted': inserted,
            'records_failed': 0,  # conteo explícito, no fetched-upserted
            'status': 'SUCCESS',
            'execution_mode': 'cron'
        })

        # 5. Actualizar checkpoint BD
        max_event_id = max(safe_int(e.get('id', 0)) for e in eventos_raw) if eventos_raw else 0
        update_checkpoint(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'last_timestamp': run_start,
            'last_event_id': max_event_id,
            'records_processed': inserted,
            'status': 'ACTIVE'
        })

        # 6. Mantener checkpoint JSON local (fallback)
        from calendario_tradingview_live_v5 import guardar_checkpoint
        guardar_checkpoint(max_event_id, inserted, len(eventos_raw))

        return inserted

    except Exception as e:
        logger.error(f"BD: Error en process_calendar_batch: {e}")
        # Registrar auditoría (fallo)
        log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'run_start': run_start,
            'records_fetched': len(eventos_raw),
            'records_upserted': 0,
            'records_failed': len(eventos_raw),
            'status': 'FAILED',
            'error_message': str(e),
            'execution_mode': 'cron'
        })
        raise

    finally:
        db.disconnect()


def safe_int(val):
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None