"""db/postgresql_connection.py — conector PostgreSQL (psycopg2).

Patrón copiado/adaptado de ``proy_heatmap/db/postgresql_connection.py``:
repositorios con SQL explícito (sin ORM), `RealDictCursor` para lectura.

Los repositorios de ``repositories/`` reciben una instancia de `PostgreSQLConnector`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence

import psycopg2
import psycopg2.extras

from core.logging_config import get_logger

logger = get_logger("db.postgresql_connection")


class PostgreSQLConnector:
    """Conexión y ejecución de consultas sobre PostgreSQL."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        connect_timeout: int = 8,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connect_timeout = connect_timeout
        self.connection = None

    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=self.connect_timeout,
            )
            self.connection.autocommit = False
            logger.debug("Conexión exitosa a %s/%s", self.host, self.database)
            return True
        except psycopg2.Error as exc:
            logger.error("Error al conectar a PostgreSQL %s/%s: %s", self.host, self.database, exc)
            return False

    def disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
            except Exception as exc:  # pragma: no cover - cierre defensivo
                logger.error("Error al cerrar conexión: %s", exc)
            finally:
                self.connection = None

    def _ensure_connection(self) -> bool:
        return True if self.connection else self.connect()

    def execute_query(self, query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """SELECT → lista de dicts. Si no hay filas, devuelve ``[{'rows_affected': n}]``."""
        if not self._ensure_connection():
            logger.warning("Sin conexión; consulta no ejecutada")
            return []
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(query, params) if params else cursor.execute(query)
            results: List[Dict[str, Any]] = []
            if cursor.description is not None:
                results = [dict(row) for row in cursor.fetchall()]
            else:
                results = [{"rows_affected": cursor.rowcount}]
            self.connection.commit()
            return results
        except psycopg2.Error as exc:
            self.connection.rollback()
            logger.error("Error SQL: %s | query=%s", exc, query)
            raise
        finally:
            cursor.close()

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        """INSERT/UPDATE/DELETE → rowcount."""
        if not self._ensure_connection():
            logger.warning("Sin conexión; sentencia no ejecutada")
            return 0
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params) if params else cursor.execute(query)
            rowcount = cursor.rowcount
            self.connection.commit()
            return rowcount
        except psycopg2.Error as exc:
            self.connection.rollback()
            logger.error("Error SQL: %s | query=%s", exc, query)
            raise
        finally:
            cursor.close()

    def execute_values(self, query: str, values: Iterable[Sequence[Any]]) -> int:
        """UPSERT masivo con ``psycopg2.extras.execute_values``. ``query`` debe contener ``%s``."""
        if not self._ensure_connection():
            logger.warning("Sin conexión; execute_values no ejecutado")
            return 0
        cursor = self.connection.cursor()
        try:
            psycopg2.extras.execute_values(cursor, query, list(values))
            rowcount = cursor.rowcount
            self.connection.commit()
            return rowcount
        except psycopg2.Error as exc:
            self.connection.rollback()
            logger.error("Error SQL (execute_values): %s", exc)
            raise
        finally:
            cursor.close()

    @contextmanager
    def cursor(self, dict_cursor: bool = True):
        """Cursor como context manager (para transacciones explícitas)."""
        if not self._ensure_connection():
            raise RuntimeError("Sin conexión a PostgreSQL")
        factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        cur = self.connection.cursor(cursor_factory=factory)
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()


def check_connection(settings) -> tuple[bool, str]:
    """Ping de salud: (ok, detalle). No lanza excepción."""
    if not settings.db_configurada:
        return False, "BD no configurada (.env sin BD_HEATMAP_*)"
    connector = PostgreSQLConnector(**settings.db_kwargs())
    try:
        if not connector.connect():
            return False, "no se pudo conectar"
        rows = connector.execute_query("SELECT 1 AS ok")
        return (bool(rows), "conexión OK")
    except Exception as exc:  # pragma: no cover - defensivo
        return False, str(exc)
    finally:
        connector.disconnect()
