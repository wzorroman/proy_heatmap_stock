"""repositories/base.py — base común de repositorios (solo SQL)."""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from db.postgresql_connection import PostgreSQLConnector


class BaseRepository:
    """Repositorio base. Si no hay conector, degrada a listas/vacíos."""

    def __init__(self, connector: Optional[PostgreSQLConnector] = None) -> None:
        self.connector = connector

    @property
    def habilitado(self) -> bool:
        return self.connector is not None

    def fetch(self, sql: str, params: Optional[Sequence[Any]] = None) -> list[dict]:
        if not self.habilitado:
            return []
        return self.connector.execute_query(sql, params)

    def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[dict]:
        rows = self.fetch(sql, params)
        if not rows:
            return None
        if "rows_affected" in rows[0]:
            return None
        return rows[0]

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> int:
        if not self.habilitado:
            return 0
        return self.connector.execute(sql, params)

    def execute_values(self, sql: str, values: Iterable[Sequence[Any]]) -> int:
        if not self.habilitado:
            return 0
        return self.connector.execute_values(sql, values)
