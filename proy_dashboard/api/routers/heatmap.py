"""api/routers/heatmap.py — treemap, sectorial y rotación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


@router.get("/treemap")
def treemap(
    limit: int = Query(default=0, ge=0, le=2000),
    container: Container = Depends(get_container),
) -> dict:
    data = container.heatmap_service.treemap(limite=limit or None)
    return {"n": len(data), "items": data}


@router.get("/sectors")
def sectors(container: Container = Depends(get_container)) -> dict:
    data = container.heatmap_service.sectores()
    return {"n": len(data), "sectores": data}


@router.get("/rotation")
def rotation(container: Container = Depends(get_container)) -> dict:
    data = container.heatmap_service.rotacion()
    return {"n": len(data), "ventanas": data}


@router.get("/distribution")
def distribution(container: Container = Depends(get_container)) -> dict:
    data = container.heatmap_service.distribucion_change()
    return {"n": len(data), "change_pct": data}
