"""api/routers/momentum.py — momentum top/bottom."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/momentum", tags=["momentum"])


@router.get("/top")
def momentum_top(
    n: int = Query(default=0, ge=0, le=200),
    container: Container = Depends(get_container),
) -> dict:
    return container.momentum_service.top_bottom(n or None)
