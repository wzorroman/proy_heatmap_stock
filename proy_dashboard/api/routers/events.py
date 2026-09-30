"""api/routers/events.py — calendario económico y sorpresas."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def eventos(
    country: Optional[str] = Query(default=None),
    importance: Optional[int] = Query(default=None, ge=-1, le=3),
    hours: int = Query(default=0, ge=0, le=24 * 30),
    container: Container = Depends(get_container),
) -> dict:
    data = container.event_service.proximos(
        country=country, importance_min=importance, horas=hours or None
    )
    return {"n": len(data), "eventos": data}


@router.get("/surprises")
def sorpresas(
    country: Optional[str] = Query(default=None),
    importance: Optional[int] = Query(default=None, ge=-1, le=3),
    container: Container = Depends(get_container),
) -> dict:
    data = container.event_service.sorpresas(country=country, importance_min=importance)
    return {"n": len(data), "sorpresas": data}
