# file: proy_scrapping_detail/scripts/load_market_csv_to_db.py
"""
Backfill one-shot: vuelca DATOS_LIVE/** (CSV activos + históricos mensuales)
a fact_market_series replicando exactamente el pipeline del scraper V5.

Reutiliza:
  - db/market_repository.insert_market_series_batch  (UPSERT ON CONFLICT DO UPDATE)
  - db/partitions.create_partition                   (particiones faltantes + BRIN)
  - db/audit_repository.log_sync_run                 (auditoría backfill_market_csv)

Uso (por etapas, con venv, cwd = proy_scrapping_detail):
  venv/bin/python3 scripts/load_market_csv_to_db.py \
      --fecha-inicio 2026-09-15 --fecha-fin 2026-09-18 --dry-run
  venv/bin/python3 scripts/load_market_csv_to_db.py \
      --fecha-inicio 2026-03-17 --fecha-fin 2026-03-18
  (sin fechas => vuelca todo el histórico + buffer activo)

Nota: los numéricos se castean como lo haría json.loads del runtime
(int sin '.', float con '.'/'e'), para que source_checksum CANÓNICO coincida
exactamente con el scraper V5 en vivo (D19).
"""
import argparse
import csv
import glob
import logging
import os
import re
import sys
from datetime import datetime, timezone

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import config
from db.postgresql_connection import PostgreSQLConnector
from db.market_repository import insert_market_series_batch, get_asset_id_cache
from db.partitions import create_partition, partition_exists
from db.audit_repository import log_sync_run

logger = logging.getLogger('load_market_csv')
BATCH_SIZE = 5000
SCRIPT_NAME = 'backfill_market_csv'
DIR_ROOTS = ('DATOS_LIVE',)
ARCHIVO_PATTERN = re.compile(r'_20\d{4}/')

# CSV: ADX,BBPower,CCI20,Perf.W,Pivot.M.Camarilla.R3,RSI,change,close,volume,timestamp_utc,fecha_iso,simbolo
_METRIC_COLS = {
    'adx': 0,
    'bbpower': 1,
    'cci20': 2,
    'perf_w': 3,
    'pivot_camarilla_r3': 4,
    'rsi': 5,
    'change_pct': 6,
    'close': 7,
    'volume': 8,
}
_TS_IDX = 9
_SYM_IDX = 11


def parse_fecha(val: str) -> datetime:
    """Acepta 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS' (asume UTC)."""
    try:
        return datetime.fromisoformat(val).replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.fromisoformat(val + 'T00:00:00').replace(tzinfo=timezone.utc)


def json_number(val: str):
    """
    Replica json.loads: int sin marcador decimal/exp, float con '.'/'e'/'E'.
    Así source_checksum coincide con el runtime (el CSV viene de to_csv de pandas).
    """
    if val is None or val.strip() == '':
        return None
    v = val.strip()
    if re.search(r'[.eE]', v):
        try:
            return float(v)
        except ValueError:
            return None
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return None


def iter_csv_files():
    """Rinde todos los CSV de DATOS_LIVE: primero históricos, luego buffer activo."""
    for root in DIR_ROOTS:
        base = os.path.join(PARENT, root)
        historics = sorted(glob.glob(os.path.join(base, '*_20*/historico_*.csv')))
        actives = sorted(glob.glob(os.path.join(base, '*/*.csv')))
        actives = [f for f in actives if not ARCHIVO_PATTERN.search(f)]
        for f in historics + actives:
            yield f


def first_last_ts(path: str):
    """Devuelve (primer_ts, ultimo_ts) del archivo; (-1, -1) si vacío."""
    with open(path, 'rb') as fh:
        header = fh.readline()
        if not header:
            return -1, -1
        first_row = fh.readline()
        if not first_row.strip():
            return -1, -1
        first_ts = int(first_row.split(b',')[_TS_IDX])
        # Última línea no vacía: leer hacia atrás desde el final
        last_ts = first_ts
        pos = fh.seek(0, 2)
        buf = b''
        while pos > 0:
            pos -= 1
            fh.seek(pos)
            c = fh.read(1)
            if c == b'\n' and buf:
                if buf.strip():
                    last_ts = int(buf.split(b',')[_TS_IDX])
                    break
                buf = b''
            elif c != b'\n':
                buf = c + buf
    return first_ts, last_ts


def data_range():
    """Rango real [min, max] de timestamp_utc en todos los CSV."""
    lo, hi = None, None
    for f in iter_csv_files():
        a, b = first_last_ts(f)
        if a > 0:
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
    return lo, hi


def months_between(start: datetime, end: datetime):
    """Meses civiles [start, end] (datetime UTC primer de mes)."""
    m = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_dt = end.replace(hour=23, minute=59, second=59)
    while m <= end_dt:
        yield m
        if m.month == 12:
            m = m.replace(year=m.year + 1, month=1, day=1)
        else:
            m = m.replace(month=m.month + 1, day=1)


def tabla_partition_exists(db, tabla: str, particion: str) -> bool:
    """Chequeo directo por nombre vía pg_class (robusto ante bounds variados)."""
    result = db.execute_query("""
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %s AND n.nspname = 'public' AND c.relkind = 'r'
    """, (particion,))
    return bool(result) and any(r.get('relname') for r in result)


def ensure_partitions(db, start: datetime, end: datetime, tabla='fact_market_series') -> int:
    """
    Crea las particiones mensuales del rango que falten (con BRIN).

    IMPORTANTE: se pasa a create_partition un mes NAIVE (sin tzinfo). Así
    PostgreSQL interpreta las fronteras en el TimeZone del servidor
    (America/Lima, -05), la MISMA convención que usa 02_init_database.sql
    ('Partition 2026-09' = medianoche local). Si se pasaran datetimes UTC,
    quedaría un gap de 5h en la frontera entre particiones de meses contiguos.
    """
    creadas = 0
    for mes in months_between(start, end):
        particion = f"{tabla}_{mes.strftime('%Y_%m')}"
        if tabla_partition_exists(db, tabla, particion):
            logger.debug(f"Partición {particion} ya existe")
            continue
        if create_partition(db, tabla, mes.replace(tzinfo=None)):
            creadas += 1
    return creadas


def build_row(fields: list) -> dict:
    row = {key: json_number(fields[idx]) for key, idx in _METRIC_COLS.items()}
    row['timestamp_utc'] = datetime.fromtimestamp(int(fields[_TS_IDX]), timezone.utc)
    row['symbol'] = fields[_SYM_IDX].strip()
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description='Backfill fact_market_series desde CSV.')
    ap.add_argument('--fecha-inicio', help='Fecha inicio (YYYY-MM-DD o ISO UTC)')
    ap.add_argument('--fecha-fin', help='Fecha fin (YYYY-MM-DD o ISO UTC)')
    ap.add_argument('--dry-run', action='store_true', help='Cuenta sin insertar')
    ap.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    ap.add_argument('-v', action='store_true', help='Log debug')
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.v else logging.INFO,
        format='%(asctime)s %(levelname)-7s %(message)s',
        handlers=[logging.StreamHandler()],
    )

    t0 = datetime.now(timezone.utc)

    if args.fecha_inicio and args.fecha_fin:
        inicio = parse_fecha(args.fecha_inicio)
        fin = parse_fecha(args.fecha_fin)
    else:
        lo, hi = data_range()
        if not lo:
            logger.error("No se encontraron filas CSV en DATOS_LIVE.")
            return 2
        inicio = datetime.fromtimestamp(lo, timezone.utc).replace(microsecond=0)
        fin = datetime.fromtimestamp(hi, timezone.utc).replace(microsecond=0)
        logger.info(f"Rango detectado desde CSV: {inicio.isoformat()} → {fin.isoformat()}")

    t_inicio = int(inicio.timestamp())
    t_fin = int(fin.timestamp())

    if not config.DB_WRITE_ENABLED and not args.dry_run:
        logger.error("DB_WRITE_ENABLED=false en .env — activa la escritura o usa --dry-run.")
        return 2

    db = PostgreSQLConnector(config.PG_HOST, config.PG_PORT,
                             config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD)
    if not db.connect():
        logger.error("No se pudo conectar a BD.")
        return 2

    total_leidas = 0
    filas_en_rango = 0
    total_convertidas = 0
    failed_simbolo = 0
    failed_fila = 0
    simbolos_vistos = set()
    simbolos_ausentes = set()
    batch: list = []
    batch_rows = 0

    try:
        if not args.dry_run:
            creadas = ensure_partitions(db, inicio, fin)
            logger.info(f"Particiones garantizadas [{inicio.date()} – {fin.date()}]: {creadas} nuevas")
        asset_cache = get_asset_id_cache(db)
        logger.info(f"Cache asset_id: {len(asset_cache)} activos")

        for f in iter_csv_files():
            rel = os.path.relpath(f, PARENT)
            with open(f, newline='', encoding='utf-8') as fh:
                reader = csv.reader(fh)
                next(reader, None)  # header
                for fields in reader:
                    if not fields or len(fields) != 12:
                        failed_fila += 1
                        continue
                    try:
                        ts = int(fields[_TS_IDX])
                    except (ValueError, TypeError):
                        failed_fila += 1
                        continue
                    total_leidas += 1
                    if ts < t_inicio or ts > t_fin:
                        continue
                    filas_en_rango += 1

                    row = build_row(fields)
                    simbolos_vistos.add(row['symbol'])
                    if row['symbol'] not in asset_cache:
                        simbolos_ausentes.add(row['symbol'])
                        failed_simbolo += 1
                        continue

                    total_convertidas += 1
                    batch.append(row)
                    batch_rows += 1
                    if batch_rows >= args.batch_size:
                        if not args.dry_run:
                            insert_market_series_batch(db, batch, asset_cache=asset_cache)
                        batch = []
                        batch_rows = 0

            logger.info(f"  Procesado: {rel}")

        if batch_rows:
            if not args.dry_run:
                insert_market_series_batch(db, batch, asset_cache=asset_cache)

        failed_total = failed_simbolo + failed_fila

        logger.info("=" * 70)
        logger.info(f"RESUMEN backfill  [{inicio.isoformat()} → {fin.isoformat()}]")
        logger.info(f"  Filas leídas en archivos     : {total_leidas}")
        logger.info(f"  Filas dentro del rango       : {filas_en_rango}")
        logger.info(f"  Filas a insertar (upsert)    : {total_convertidas}")
        logger.info(f"  Filas fallidas (símbolo)     : {failed_simbolo}")
        logger.info(f"  Filas fallidas (fila mala)   : {failed_fila}")
        logger.info(f"  Símbolos distintos vistos    : {len(simbolos_vistos)}")
        if simbolos_ausentes:
            logger.warning(f"  Símbolos AUSENTES en dim_asset: "
                           f"{len(simbolos_ausentes)} -> {sorted(simbolos_ausentes)}")

        if not args.dry_run:
            log_sync_run(db, {
                'script_name': SCRIPT_NAME,
                'run_start': t0,
                'records_fetched': filas_en_rango,
                'records_upserted': total_convertidas,
                'records_failed': failed_total,
                'status': 'SUCCESS',
                'execution_mode': 'manual',
            })
            logger.info(f"Auditoría registrada: {SCRIPT_NAME} - SUCCESS "
                        f"(fetched={filas_en_rango}, upserted={total_convertidas}, "
                        f"failed={failed_total})")
        else:
            logger.info("DRY-RUN: no se insertó nada ni se registró auditoría.")

        logger.info(f"Tiempo total: {(datetime.now(timezone.utc) - t0).total_seconds():.1f} s")
        return 0

    except Exception as e:
        logger.exception(f"Error durante el backfill: {e}")
        if not args.dry_run:
            try:
                log_sync_run(db, {
                    'script_name': SCRIPT_NAME,
                    'run_start': t0,
                    'records_fetched': filas_en_rango,
                    'records_upserted': 0,
                    'records_failed': filas_en_rango,
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