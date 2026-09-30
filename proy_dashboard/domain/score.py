"""domain/score.py — dataclasses del score de mercado."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ComponenteScore:
    """Contribución de un indicador al score de un activo."""

    nombre: str
    valor: Optional[float]
    norm: Optional[float]  # [0,1] o None si el valor es NaN
    peso: float


@dataclass
class ScoreActivo:
    """Score por activo (PASO 1)."""

    asset_id: int
    symbol: str
    score_general: Optional[float]
    zona: str = "NEUTRAL"
    componentes: List[ComponenteScore] = field(default_factory=list)


@dataclass
class ScoreMercado:
    """Agregado de mercado por ciclo (PASO 2/2b/3)."""

    timestamp_utc: datetime
    score_momentum: Optional[float] = None
    score_15min: Optional[float] = None
    score_radar: Optional[float] = None
    score_market: Optional[float] = None
    zona: str = "NEUTRAL"
    n_simbolos: int = 0
    pesos: Dict[str, float] = field(default_factory=dict)
    zonas: Dict[str, float] = field(default_factory=dict)
