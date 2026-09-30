"""domain — dataclasses puras (sin dependencias de infraestructura)."""

from domain.event import EventoEconomico
from domain.market import ActivoTick, RiesgoItem, SectorSnapshot
from domain.score import ComponenteScore, ScoreActivo, ScoreMercado

__all__ = [
    "ComponenteScore",
    "ScoreActivo",
    "ScoreMercado",
    "ActivoTick",
    "SectorSnapshot",
    "RiesgoItem",
    "EventoEconomico",
]
