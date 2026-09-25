#!/usr/bin/env python3
"""
CREACIÓN DE PARTICIONES MENSUALES - POSTGRESQL
==============================================
Script: create_partitions.py
Descripción: Verifica y crea particiones mensuales para las tablas de hechos
             (fact_heatmap_snapshot, fact_market_series) desde el mes actual
             hasta N meses hacia adelante.

Uso:
    # Crear particiones para 3 meses futuros (default)
    python create_partitions.py

    # Crear particiones para 6 meses futuros
    python create_partitions.py --months 6

    # Crear particiones solo para una tabla específica
    python create_partitions.py --table fact_heatmap_snapshot

    # Crear particiones para todas las tablas configuradas
    python create_partitions.py --all

Dependencias:
    - psycopg2-binary
    - python-dotenv

# --- comprobar en sql ---
    SELECT
        child.relname AS partition_name,
        pg_get_expr(child.relpartbound, child.oid) AS partition_range
    FROM pg_inherits
    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
    JOIN pg_class child  ON pg_inherits.inhrelid = child.oid
    JOIN pg_namespace n ON n.oid = parent.relnamespace
    WHERE parent.relname = 'fact_heatmap_snapshot'
    AND n.nspname = 'public'
    ORDER BY child.relname;

Uso:
    python create_partitions.py --all --months 3
"""

import os
import sys
import argparse
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.config_logging import get_logger
from db.postgresql_connection import PostgreSQLConnector

logger = get_logger('create_partitions')

TABLAS_POR_DEFECTO = ["fact_heatmap_snapshot", "fact_market_series"]
# Tablas cuyas particiones requieren índice BRIN por timestamp_utc
# (PostgreSQL 15 no propaga BRIN desde el padre; se crea por partición).
BRIN_TABLES = ["fact_market_series"]
SCHEMA = "public"


def _extract_bounds(result) -> Optional[str]:
    """Extrae el primer valor escalar de cualquier estructura que devuelva el conector."""
    if not result:
        return None
    row = result[0]
    if row is None:
        return None
    if isinstance(row, dict):
        for key in ('bounds', 'reg'):
            if key in row:
                return row[key]
        return next(iter(row.values()), None)
    if isinstance(row, (tuple, list)):
        return row[0] if row else None
    return None  # e.g., una cadena suelta u otro tipo


def partition_exists(conn, table_name, partition_name, start_date, end_date) -> bool:
    query = """
        SELECT pg_get_expr(c.relpartbound, c.oid) AS bounds
        FROM pg_class c
        JOIN pg_namespace cn ON cn.oid = c.relnamespace
        JOIN pg_inherits i ON i.inhrelid = c.oid
        JOIN pg_class p ON i.inhparent = p.oid
        JOIN pg_namespace pn ON pn.oid = p.relnamespace
        WHERE c.relname = %s AND cn.nspname = %s
          AND p.relname = %s AND pn.nspname = %s
    """
    result = conn.execute_query(query, (partition_name, SCHEMA, table_name, SCHEMA))
    actual = _extract_bounds(result)

    if actual:
        # Tolerante al TimeZone del servidor: el límite puede renderizarse como
        # '+00' (UTC) o '-05' (local). Se valida por año/mes/día en vez de
        # comparar instantes exactos, evitando falsos "rango distinto".
        m = re.search(r"FROM \('([^']+)'\) TO \('([^']+)'\)", actual)
        if m:
            try:
                # Solo la parte de fecha (YYYY-MM-DD): ignora el offset ("-05"/"-05:00")
                # y evita el ValueError de fromisoformat en Python < 3.11.
                b_from = datetime.fromisoformat(m.group(1)[:10]).date()
                b_to = datetime.fromisoformat(m.group(2)[:10]).date()
            except ValueError:
                b_from = b_to = None
            expected_year, expected_month = start_date.year, start_date.month
            expected_to_year = expected_year + (1 if expected_month == 12 else 0)
            expected_to_month = (expected_month % 12) + 1
            if (b_from is not None and b_to is not None
                    and b_from.year == expected_year
                    and b_from.month == expected_month
                    and b_from.day == 1
                    and b_to.year == expected_to_year
                    and b_to.month == expected_to_month
                    and b_to.day == 1):
                return True

    if actual is None and not result:
        return False  # simplemente no existe → create_partition la crea

    # Llegamos aquí: existe pero con rango distinto (o bounds irreconocible)
    logger.warning(f"⚠️  {partition_name}: rango actual={actual!r}, "
                   f"esperado={start_date} a {end_date}. Se recreará.")

    # Protección: solo dropear si realmente existe y está vacía
    chk = conn.execute_query(
        "SELECT to_regclass(%s) AS reg", (f"{SCHEMA}.{partition_name}",)
    )
    reg = _extract_bounds(chk)
    if reg:  # to_regclass devuelve el nombre calificado o NULL
        n = _extract_bounds(conn.execute_query(
            f"SELECT COUNT(*) FROM {SCHEMA}.{partition_name}"))
        if n and int(n) > 0:
            raise RuntimeError(
                f"{partition_name} tiene {n} filas con rango incorrecto; "
                f"no se recrea automáticamente"
            )
        conn.execute_query(f"DROP TABLE IF EXISTS {SCHEMA}.{partition_name}")
    return False


def ensure_brin_for_partition(conn: PostgreSQLConnector, table_name: str, partition_name: str) -> None:
    """Crea el índice BRIN por timestamp_utc en la partición si aplica."""
    if table_name not in BRIN_TABLES:
        return
    index_name = f"{partition_name}_ts_brin"
    conn.execute_query(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {partition_name} USING BRIN (timestamp_utc)"
    )
    logger.debug(f"✅ BRIN {index_name} asegurado sobre {partition_name}")


def create_partition(conn: PostgreSQLConnector, table_name: str, partition_name: str,
                     start_date: datetime, end_date: datetime) -> bool:
    """Crea una partición mensual si no existe."""
    if partition_exists(conn, table_name, partition_name, start_date, end_date):
        logger.debug(f"Partición {partition_name} ya existe")
        return False

    create_query = f"""
        CREATE TABLE {partition_name} PARTITION OF {table_name}
        FOR VALUES FROM (%s) TO (%s)
    """
    conn.execute_query(create_query, (start_date, end_date))
    logger.info(f"✅ Partición {partition_name} creada ({start_date.date()} - {end_date.date()})")
    ensure_brin_for_partition(conn, table_name, partition_name)
    return True


def ensure_table_is_partitioned(conn: PostgreSQLConnector, table_name: str) -> bool:
    """Verifica que la tabla exista y esté particionada por RANGE."""
    query = """
        SELECT c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %s AND n.nspname = %s
    """
    result = conn.execute_query(query, (table_name, SCHEMA))
    if not result:
        logger.error(f"❌ Tabla {table_name} no existe en {SCHEMA}")
        return False
    relkind = result[0].get('relkind')
    if relkind != 'p':
        logger.error(f"❌ Tabla {table_name} no está particionada (relkind={relkind})")
        return False
    return True


def create_monthly_partitions(conn: PostgreSQLConnector, table_name: str,
                              months_ahead: int = 3, start_date: Optional[datetime] = None) -> int:
    """Crea particiones mensuales para una tabla desde start_date hasta months_ahead meses."""
    if start_date is None:
        start_date = datetime.now(timezone.utc)
    start_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if not ensure_table_is_partitioned(conn, table_name):
        return 0

    created = 0
    for i in range(months_ahead + 1):
        target = start_date + timedelta(days=i * 32)
        target = target.replace(day=1)
        partition_name = f"{table_name}_{target.strftime('%Y_%m')}"
        end_date = (target + timedelta(days=32)).replace(day=1)

        if create_partition(conn, table_name, partition_name, target, end_date):
            created += 1

    logger.info(f"📊 {table_name}: {created} nuevas, {months_ahead + 1 - created} ya existían")
    return created


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", "-m", type=int, default=3, help="Meses futuros (default: 3)")
    parser.add_argument("--table", "-t", type=str, help="Tabla específica")
    parser.add_argument("--all", "-a", action="store_true", help="Todas las tablas")
    parser.add_argument("--start-date", "-s", type=str, help="YYYY-MM-DD (default: hoy)")
    args = parser.parse_args()

    logger.info("=== INICIO CREACIÓN DE PARTICIONES ===")

    start_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    db = PostgreSQLConnector(
        host=config.PG_HOST, port=config.PG_PORT,
        database=config.PG_DATABASE, user=config.PG_USER, password=config.PG_PASSWORD
    )
    if not db.connect():
        logger.error("❌ No se pudo conectar a PostgreSQL")
        sys.exit(1)

    try:
        tablas = [args.table] if args.table else (TABLAS_POR_DEFECTO if args.all else [TABLAS_POR_DEFECTO[0]])
        total = 0
        for tbl in tablas:
            total += create_monthly_partitions(db, tbl, args.months, start_date)
        logger.info(f"✅ Proceso completado. Total particiones creadas: {total}")
    except Exception as e:
        logger.exception(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.disconnect()

    logger.info("=== FIN CREACIÓN DE PARTICIONES ===")


if __name__ == "__main__":
    main()