"""api/schemas.py — modelos Pydantic del borde de la API."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel


class VersionResponse(BaseModel):
    app: str
    version: str
    env: str


class HealthResponse(BaseModel):
    status: str
    app: Dict[str, Any]
    modulos: Dict[str, Any]
    timestamp_utc: str
