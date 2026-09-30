"""domain/market.py — dataclasses de mercado (ticks, sectores, riesgo)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ActivoTick:
    """Último tick de un activo (fuente: latest_market_tick)."""

    asset_id: int
    symbol: str
    timestamp_utc: datetime
    asset_class: Optional[str] = None
    close: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    rsi: Optional[float] = None
    rsi_15: Optional[float] = None
    cci20_15: Optional[float] = None
    bbpower_15: Optional[float] = None
    adx_15: Optional[float] = None
    pivot_r3_15: Optional[float] = None


@dataclass
class SectorSnapshot:
    """Agregado de un sector sobre una ventana del heatmap."""

    sector: str
    n_activos: int = 0
    change_medio: Optional[float] = None
    market_cap_total: Optional[float] = None
    ganadores: int = 0
    perdedores: int = 0


@dataclass
class RiesgoItem:
    """Componente del termómetro de riesgo intermarket."""

    logical_key: str
    symbol: str
    valor: Optional[float] = None
    change_pct: Optional[float] = None
    rsi: Optional[float] = None
    norm_dir: Optional[float] = None
    estado: str = "NEUTRAL"
