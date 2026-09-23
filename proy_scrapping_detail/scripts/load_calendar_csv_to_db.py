# file: proy_scrapping_detail/scripts/load_calendar_csv_to_db.py
"""
Backfill one-shot: vuelca los CSV del calendario económico (esquema V5)
a fact_economic_event replicando exactamente el pipeline del scraper V5.

Reutiliza:
  - db/event_repository.insert_events_batch   (UPSERT ON CONFLICT DO UPDATE)
  - db/audit_repository.log_sync_run          (auditoría backfill_calendar_csv)
  - db/audit_repository.update_checkpoint     (checkpoint de 'calendario')

Alcance:
  - eventos_calendario.csv (archivo principal actual)
  - */historico_*.csv con esquema V5 (contienen 'id' + 'timestamp_captura').
  Los historicos de esquema V3/V4 (sin id) se omiten con warning:
  no tienen event_id estable y no pueden poblar la PK de fact_economic_event.

Uso (con venv, cwd = proy_scrapping_detail):
  venv/bin/python3 scripts/load_calendar_csv_to_db.py --dry-run
  venv/bin/python3 scripts/load_calendar_csv_to_db.py
"""
import argparse
import csv
import glob
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import config
from db.postgresql_connection import PostgreSQLConnector
from db.event_repository import insert_events_batch, safe_int
from db.audit_repository import log_sync_run, update_checkpoint

logger = logging.getLogger('load_calendar_csv')
BATCH_SIZE = 500
SCRIPT_NAME = 'backfill_calendar_csv'
CALENDARIO_DIR = os.path.join(PARENT, 'DATOS_LIVE_CALENDARIO', 'calendario_economico')

# Cabecera mínima del esquema V5 (id + timestamp_captura) exigida para cargar.
V5_REQUIRED = ('id', 'timestamp_captura')


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iter_v5_csv_files():
    """
    Rinde los CSV V5: primero historicos (antiguo->nuevo), luego el principal
    al final para que sus valores ganen en conflictos por event_id.
    """
    historics = sorted(glob.glob(os.path.join(CALENDARIO_DIR, '*', 'historico_*.csv')))
    main_file = os.path.join(CALENDARIO_DIR, 'eventos_calendario.csv')
    for f in historics + ([main_file] if os.path.exists(main_file) else []):
        yield f


def detect_schema(path: str) -> bool:
    """True si el CSV tiene las columnas del esquema V5."""
    try:
        with open(path, newline='', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if not header:
                return False
            cols = [c.strip() for c in header]
            return all(col in cols for col in V5_REQUIRED)
    except (OSError, StopIteration):
        return False


def build_event(row: dict) -> dict:
    """Traduce una fila CSV a dict crudo ('' -> None) como lo haria la API."""
    return {k: (v if v != '' else None) for k, v in row.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description='Backfill fact_economic_event desde CSV V5.')
    ap.add_argument('--dry-run', action='store_true', help='Cuenta sin insertar')
    ap.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    ap.add_argument('--no-checkpoint', action='store_true',
                    help='No actualizar sync_checkpoint de "calendario"')
    ap.add_argument('-v', action='store_true', help='Log debug')
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.v else logging.INFO,
        format='%(asctime)s %(levelname)-7s %(message)s',
        handlers=[logging.StreamHandler()],
    )

    t0 = now_utc()

    if not os.path.isdir(CALENDARIO_DIR):
        logger.error(f"Directorio de calendario no encontrado: {CALENDARIO_DIR}")
        return 2

    if not config.DB_WRITE_ENABLED and not args.dry_run:
        logger.error("DB_WRITE_ENABLED=false en .env — activa la escritura o usa --dry-run.")
        return 2

    # 1. Recorrer archivos y recolectar eventos V5 (dedup por event_id).
    eventos_por_id: dict = {}
    archivos_procesados = []
    archivos_omitidos = []
    filas_leidas = 0
    encontrados = 0

    for f in iter_v5_csv_files():
        if not detect_schema(f):
            rel = os.path.relpath(f, PARENT)
            archivos_omitidos.append(rel)
            logger.warning(f"Omitido (esquema V3/V4 sin id): {rel}")
            continue
        with open(f, newline='', encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh)
            ncols = len(reader.fieldnames or [])
            for row in reader:
                if len([c for c in (row.get('id') or '').strip()]) == 0:
                    continue
                eid = safe_int(row.get('id'))
                if eid is None:
                    continue
                eventos_por_id[eid] = build_event(row)
                filas_leidas += 1
        rel = os.path.relpath(f, PARENT)
        archivos_procesados.append(rel)
        encontrados += 1

    if not eventos_por_id:
        logger.error("No se encontraron eventos V5 para cargar.")
        return 2

    eventos = list(eventos_por_id.values())
    total_unicos = len(eventos)
    paises = Counter(e.get('country') for e in eventos)
    max_event_id = max(int(k) for k in eventos_por_id)

    logger.info("=" * 70)
    logger.info(f"RESUMEN lectura  [{now_utc().isoformat()}]")
    logger.info(f"  Archivos V5 procesados     : {encontrados} -> {archivos_procesados}")
    if archivos_omitidos:
        logger.warning(f"  Archivos omitidos (V3/V4) : {len(archivos_omitidos)} -> {archivos_omitidos}")
    logger.info(f"  Filas leidas (con id)      : {filas_leidas}")
    logger.info(f"  Eventos unicos (dedup)     : {total_unicos}")
    logger.info(f"  Paises                     : {', '.join(f'{p}({n})' for p, n in sorted(paises.items()))}")
    logger.info(f"  Max event_id               : {max_event_id}")

    if args.dry_run:
        logger.info("DRY-RUN: no se inserto nada ni se registro auditoria.")
        return 0

    # 2. Conectar a BD
    db = PostgreSQLConnector(config.PG_HOST, config.PG_PORT,
                             config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD)
    if not db.connect():
        logger.error("No se pudo conectar a BD.")
        return 2

    upserted = 0
    try:
        for i in range(0, len(eventos), args.batch_size):
            chunk = eventos[i:i + args.batch_size]
            upserted += insert_events_batch(db, chunk)
            logger.info(f"  Lote {i + len(chunk)}/{len(eventos)}: {len(chunk)} eventos")

        log_sync_run(db, {
            'script_name': SCRIPT_NAME,
            'run_start': t0,
            'records_fetched': filas_leidas,
            'records_upserted': upserted,
            'records_failed': 0,
            'status': 'SUCCESS',
            'execution_mode': 'manual',
        })
        logger.info(f"Auditoría registrada: {SCRIPT_NAME} - SUCCESS "
                    f"(fetched={filas_leidas}, upserted={upserted})")

        if not args.no_checkpoint:
            update_checkpoint(db, {
                'script_name': config.SCRIPT_NAME_CALENDARIO,
                'last_timestamp': t0,
                'last_event_id': max_event_id,
                'records_processed': upserted,
                'status': 'ACTIVE',
            })
            logger.info(f"Checkpoint 'calendario' actualizado: event_id={max_event_id}")

        logger.info(f"Tiempo total: {(now_utc() - t0).total_seconds():.1f} s")
        return 0

    except Exception as e:
        logger.exception(f"Error durante el backfill: {e}")
        try:
            log_sync_run(db, {
                'script_name': SCRIPT_NAME,
                'run_start': t0,
                'records_fetched': filas_leidas,
                'records_upserted': 0,
                'records_failed': filas_leidas,
                'status': 'FAILED',
                'error_message': str(e),
                'execution_mode': 'manual',
            })
        except Exception as audit_error:
            logger.error(f"No se pudo registrar auditoría de fallo: {audit_error}")
        return 1
    finally:
        db.disconnect()


if __name__ == '__main__':
    sys.exit(main())