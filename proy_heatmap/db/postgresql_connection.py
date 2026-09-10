# file: proy_heatmap/db/postgresql_connection.py
from utils.config_logging import get_logger
from typing import List, Dict, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras

logger = get_logger('db.postgresql_connection')


class PostgreSQLConnector:
    """
    Clase para conectarse a una base de datos PostgreSQL y realizar consultas.
    Sigue el mismo patrón que MSSQLConnector.
    """

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        logger.debug(f"Inicializado PostgreSQLConnector para servidor: {self.host}/{self.database}")

    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
            )
            self.connection.autocommit = False
            logger.debug(f"Conexión exitosa a {self.host}/{self.database}")
            return True
        except psycopg2.Error as e:
            logger.critical(f"Error al conectar a PostgreSQL {self.host}/{self.database}: {e}")
            return False

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.debug(f"Conexión cerrada para {self.host}/{self.database}")
            except Exception as e:
                logger.error(f"Error al cerrar conexión: {e}")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        if not self.connection:
            if not self.connect():
                logger.warning("No se pudo establecer conexión para ejecutar query")
                return []

        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = []
            if cursor.description is not None:
                results = [dict(row) for row in cursor.fetchall()]

            self.connection.commit()

            logger.debug(f"Query ejecutada exitosamente. Resultados: {len(results)} registros")
            return results if results else [{"rows_affected": cursor.rowcount}]

        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Error de SQL al ejecutar consulta. Query: {query}. Error: {e}")
            raise e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inesperado al ejecutar query: {e}")
            raise e
        finally:
            cursor.close()

    def execute_batch(self, query: str, params_list: List[tuple]) -> int:
        if not self.connection:
            if not self.connect():
                logger.warning("No se pudo establecer conexión para batch")
                return 0

        cursor = self.connection.cursor()
        try:
            psycopg2.extras.execute_batch(cursor, query, params_list)
            self.connection.commit()
            count = len(params_list)
            logger.debug(f"Batch ejecutado exitosamente. {count} registros")
            return count
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Error en batch. Query: {query}. Error: {e}")
            raise e
        finally:
            cursor.close()

    def execute_values(self, query: str, params_list: List[tuple], template: str = None) -> List[Dict]:
        """
        Ejecuta INSERT/UPDATE con RETURNING usando execute_values.
        Retorna List[Dict] con las filas retornadas (ej: ids).
        """
        if not self.connection:
            if not self.connect():
                logger.warning("No se pudo establecer conexión para execute_values")
                return []

        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            psycopg2.extras.execute_values(
                cursor, query, params_list,
                template=template
            )

            results = []
            if cursor.description is not None:
                results = [dict(row) for row in cursor.fetchall()]

            self.connection.commit()
            logger.debug(f"execute_values: {len(results)} filas retornadas de {len(params_list)} params")
            return results if results else [{"rows_affected": cursor.rowcount}]

        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Error en execute_values. Query: {query}. Error: {e}")
            raise e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inesperado en execute_values: {e}")
            raise e
        finally:
            cursor.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
