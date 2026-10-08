"""api/routers/trading15m.py — endpoints JSON para trading a 15 min."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/trading15m", tags=["trading15m"])


@router.get("/velas")
def velas_15m(
    symbol: str = Query(default=""),
    hours: int = Query(default=0, ge=0, le=168),
    container: Container = Depends(get_container),
) -> dict:
    default = container.settings.business("trading_15m", "default_symbol", default="NASDAQ:NVDA")
    symbol = (symbol or default).upper().strip()
    data = container.bar_15m_service.analyze(symbol, horas=hours or None)
    return {"symbol": symbol, "sin_datos": data.get("sin_datos", False), "data": data}


@router.get("/screener")
def screener_15m(container: Container = Depends(get_container)) -> dict:
    filas = container.screener_15m_service.scan()
    return {"n": len(filas), "filas": filas}


@router.get("/confluencia")
def confluencia(container: Container = Depends(get_container)) -> dict:
    filas = container.confluencia_service.scan()
    return {"n": len(filas), "filas": filas}


@router.get("/oportunidades")
def oportunidades_15m(container: Container = Depends(get_container)) -> dict:
    filas = container.oportunidad_15m_service.scan()
    return {"n": len(filas), "filas": filas}


@router.get("/bollinger")
def bollinger_15m(container: Container = Depends(get_container)) -> dict:
    filas = container.bollinger_15m_service.scan()
    return {"n": len(filas), "filas": filas}
