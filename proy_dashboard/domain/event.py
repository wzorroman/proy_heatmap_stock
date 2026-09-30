"""domain/event.py — dataclasses del calendario económico."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EventoEconomico:
    """Evento del calendario económico (fact_economic_event)."""

    event_id: int
    title: str
    event_timestamp: datetime
    country: Optional[str] = None
    categoria: Optional[str] = None
    importance: Optional[int] = None
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    sorpresa_pct: Optional[float] = None
    pasado: bool = False
