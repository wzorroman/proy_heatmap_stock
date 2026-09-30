"""api/routers/indicators.py — indicadores por activo e histogramas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/indicators", tags=["indicators"])

_PERMITIDOS = {"rsi", "adx", "cci20", "bbpower"}


@router.get("")
def indicadores(
    ind: str = Query(default="rsi"),
    tf: str = Query(default="1d"),
    n: int = Query(default=0, ge=0, le=200),
    container: Container = Depends(get_container),
) -> dict:
    if ind not in _PERMITIDOS:
        return {"estado": "WARN", "detalle": f"indicador inválido: {ind}", "items": []}
    data = container.indicator_service.por_indicador(ind, tf, n or None)
    return {"indicador": ind, "tf": tf, "n": len(data), "items": data}


@router.get("/histogram")
def histograma(
    ind: str = Query(default="rsi"),
    tf: str = Query(default="1d"),
    bins: int = Query(default=10, ge=2, le=50),
    container: Container = Depends(get_container),
) -> dict:
    if ind not in _PERMITIDOS:
        return {"estado": "WARN", "detalle": f"indicador inválido: {ind}", "edges": [], "counts": []}
    hist = container.indicator_service.histograma(ind, tf, bins)
    hist.update({"indicador": ind, "tf": tf})
    return hist
