# file: proy_scrapping_detail/db/audit_repository.py
import logging
from typing import Dict, Any
from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.audit_repository')


def log_sync_run(db: PostgreSQLConnector, data: Dict[str, Any]) -> int:
    """
    Registra una ejecución en audit_sync_run.
    data contiene: script_name, run_start, run_end, records_fetched,
    records_upserted, records_failed, status, error_message, execution_mode
    """
    query = """
        INSERT INTO audit_sync_run (
            script_name, run_start, run_end,
            records_fetched, records_upserted, records_failed,
            status, error_message, execution_mode
        ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data.get('script_name'),
        data.get('run_start'),
        data.get('records_fetched', 0),
        data.get('records_upserted', 0),
        data.get('records_failed', 0),
        data.get('status', 'UNKNOWN'),
        data.get('error_message'),
        data.get('execution_mode', 'cron')
    )
    result = db.execute_query(query, params)
    logger.info(f"Auditoría registrada: {data.get('script_name')} - {data.get('status')}")
    return 1 if result else 0


def update_checkpoint(db: PostgreSQLConnector, data: Dict[str, Any]) -> int:
    """
    Actualiza el checkpoint de reanudación.
    data contiene: script_name, last_timestamp, last_event_id,
    records_processed, status
    """
    query = """
        INSERT INTO sync_checkpoint (
            script_name, last_timestamp, last_event_id,
            records_processed, last_run_at, status
        ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (script_name) DO UPDATE SET
            last_timestamp    = EXCLUDED.last_timestamp,
            last_event_id     = EXCLUDED.last_event_id,
            records_processed = EXCLUDED.records_processed,
            last_run_at       = EXCLUDED.last_run_at,
            status            = EXCLUDED.status
    """
    params = (
        data.get('script_name'),
        data.get('last_timestamp'),
        data.get('last_event_id'),
        data.get('records_processed', 0),
        data.get('status', 'ACTIVE')
    )
    result = db.execute_query(query, params)
    logger.info(f"Checkpoint actualizado: {data.get('script_name')} - event_id={data.get('last_event_id')}")
    return 1 if result else 0