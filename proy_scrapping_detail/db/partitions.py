# file: proy_scrapping_detail/db/partitions.py
"""
Utilidades locales de particionamiento (minimum viable).
Solo verifica la partición del mes actual y la crea si falta (caso excepcional).
No se importa nada de proy_heatmap: copia autónoma del patrón create_partitions.py.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.partitions')

SCHEMA = "public"
BRIN_TABLES = {"fact_market_series"}


def partition_name(tabla: str, mes: datetime) -> str:
    """Devuelve el nombre de partición {tabla}_{YYYY_MM}."""
    return f"{tabla}_{mes.strftime('%Y_%m')}"


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
    return str(row)


def partition_exists(conn: PostgreSQLConnector, tabla: str, particion: str,
                     start_date: datetime, end_date: datetime) -> bool:
    """Verifica que la partición exista y cubra el rango mensual esperado."""
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
    result = conn.execute_query(query, (particion, SCHEMA, tabla, SCHEMA))
    actual = _extract_bounds(result)

    if actual:
        m = re.search(r"FROM \('([^']+)'\) TO \('([^']+)'\)", actual)
        if m:
            # Comparar SOLO la parte de fecha (YYYY-MM-DD): ignora el offset
            # horario ("-05" / "-05:00") que PostgreSQL devuelve según la
            # sesión, y evita el ValueError de fromisoformat en Python < 3.11
            # con offsets sin minutos.
            try:
                b_from = datetime.fromisoformat(m.group(1)[:10]).date()
                b_to = datetime.fromisoformat(m.group(2)[:10]).date()
            except ValueError:
                b_from = b_to = None
            if (b_from is not None and b_to is not None
                    and b_from == start_date.date()
                    and b_to == end_date.date()):
                return True

    if actual is None and not result:
        return False
    return False


def ensure_brin_for_partition(conn: PostgreSQLConnector, tabla: str, particion: str) -> None:
    """Crea el índice BRIN por timestamp_utc en la partición si la tabla aplica."""
    if tabla not in BRIN_TABLES:
        return
    index_name = f"{particion}_ts_brin"
    conn.execute_query(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {particion} USING BRIN (timestamp_utc)"
    )
    logger.debug(f"BRIN {index_name} asegurado sobre {particion}")


def create_partition(conn: PostgreSQLConnector, tabla: str, mes: datetime) -> bool:
    """Crea la partición mensual si no existe (caso excepcional)."""
    particion = partition_name(tabla, mes)
    if mes.month == 12:
        end_date = mes.replace(year=mes.year + 1, month=1, day=1)
    else:
        end_date = mes.replace(month=mes.month + 1, day=1)
    start_date = mes.replace(day=1)

    if partition_exists(conn, tabla, particion, start_date, end_date):
        return False

    create_query = f"""
        CREATE TABLE {particion} PARTITION OF {tabla}
        FOR VALUES FROM (%s) TO (%s)
    """
    conn.execute_query(create_query, (start_date, end_date))
    logger.info(f"Partición {particion} creada ({start_date.date()} - {end_date.date()})")
    ensure_brin_for_partition(conn, tabla, particion)
    return True


def _end_of_month(mes: datetime) -> datetime:
    """Devuelve el primer día del mes siguiente."""
    if mes.month == 12:
        return mes.replace(year=mes.year + 1, month=1, day=1)
    return mes.replace(month=mes.month + 1, day=1)


def ensure_current_month_partition(conn: PostgreSQLConnector, tabla: str) -> bool:
    """
    Verifica y, solo si falta, crea la partición del mes actual.
    Retorna True si la partición está garantizada (existía o se creó).

    NOTA (fix 2026-09-18): al crear la partición se pasa el mes NAIVE
    (sin tzinfo) para que PostgreSQL interprete las fronteras en el TimeZone
    del servidor (America/Lima, -05), la MISMA convención que usa
    proy_heatmap/scripts/02_init_database.sql. Si se pasara un datetime UTC,
    la partición quedaría con medianoche UTC y habría un gap de 5h en la
    frontera con la partición del mes siguiente (y solapamiento con la previa).
    """
    now = datetime.now(timezone.utc)
    mes_actual = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = _end_of_month(mes_actual)

    if partition_exists(conn, tabla, partition_name(tabla, mes_actual), mes_actual, end_date):
        logger.debug(f"Partición {partition_name(tabla, mes_actual)} ya existe")
        return True

    logger.warning(f"Partición del mes actual ausente — creando (caso excepcional)")
    create_partition(conn, tabla, mes_actual.replace(tzinfo=None))
    return partition_exists(conn, tabla, partition_name(tabla, mes_actual), mes_actual, end_date)