"""api/routers/health.py — salud y versión."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_container
from api.schemas import HealthResponse, VersionResponse
from core.container import Container

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(container: Container = Depends(get_container)) -> dict:
    return container.health_service.check()


@router.get("/version", response_model=VersionResponse)
def version(container: Container = Depends(get_container)) -> dict:
    s = container.settings
    return {"app": s.app_name, "version": s.version, "env": s.app_env}
