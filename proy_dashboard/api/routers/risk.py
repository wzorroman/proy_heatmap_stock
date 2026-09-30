"""api/routers/risk.py — termómetro de riesgo intermarket."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.deps import get_container
from core.container import Container

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("")
def riesgo(container: Container = Depends(get_container)) -> dict:
    score, items = container.score_service.score_radar()
    return {
        "score_radar": score,
        "componentes": [asdict(i) for i in items],
    }
