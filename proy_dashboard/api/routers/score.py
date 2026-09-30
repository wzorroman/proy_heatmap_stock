"""api/routers/score.py — score de mercado (actual e histórico)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta

from fastapi import APIRouter, Depends, Query

from api.deps import get_container
from core.container import Container
from core.timezone import now_utc

router = APIRouter(prefix="/api/score", tags=["score"])


@router.get("/latest")
def score_latest(container: Container = Depends(get_container)) -> dict:
    scores, mercado = container.score_service.calcular_ciclo()
    return {"mercado": asdict(mercado), "n_activos": len(scores)}


@router.get("/history")
def score_history(
    hours: int = Query(default=0, ge=0, le=24 * 30),
    container: Container = Depends(get_container),
) -> dict:
    horas = hours or int(container.settings.business("panels", "history_hours_default", default=24))
    since = now_utc() - timedelta(hours=horas)
    rows = container.score_repo.fetch_agg_history(since)
    return {"hours": horas, "history": rows}
