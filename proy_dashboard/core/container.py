"""core/container.py — inyección de dependencias (wiring manual).

Un único contenedor construye settings, conector PostgreSQL, repositorios y
servicios, y los inyecta por constructor. Los repositorios funcionan sin conector
(degradan a vacío), lo que permite arrancar el dashboard aunque la BD no esté
configurada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.logging_config import get_logger
from core.settings import Settings, get_settings
from db.postgresql_connection import PostgreSQLConnector
from repositories import (
    Bar15mRepository,
    EventsRepository,
    HeatmapRepository,
    IndicatorTfRepository,
    LatestTickRepository,
    ScoreRepository,
    SeriesRepository,
    SessionRepository,
)
from services.bar_15m_service import Bar15mService
from services.bollinger_15m_service import Bollinger15mService
from services.confluencia_service import ConfluenciaService
from services.divergencia_5m_service import Divergencia5mService
from services.divergencia_service import DivergenciaService
from services.event_service import EventService
from services.health_service import HealthService
from services.heatmap_service import HeatmapService
from services.indicator_service import IndicatorService
from services.initial_balance_service import InitialBalanceService
from services.momentum_service import MomentumService
from services.oportunidad_15m_service import Oportunidad15mService
from services.precio_service import PrecioService
from services.screener_15m_service import Screener15mService
from services.score_service import ScoreService
from services.sector_15m_service import Sector15mService
from services.session_service import SessionService
from services.tendencia_15m_service import Tendencia15mService
from services.vwap_ib_service import VwapIbService


@dataclass
class Container:
    """Contenedor de dependencias del dashboard."""

    settings: Settings
    connector: Optional[PostgreSQLConnector] = None

    # repositorios (solo SQL)
    latest_tick_repo: Optional[LatestTickRepository] = None
    score_repo: Optional[ScoreRepository] = None
    heatmap_repo: Optional[HeatmapRepository] = None
    events_repo: Optional[EventsRepository] = None
    series_repo: Optional[SeriesRepository] = None
    indicator_repo: Optional[IndicatorTfRepository] = None
    session_repo: Optional[SessionRepository] = None
    bar_repo: Optional[Bar15mRepository] = None

    # servicios (negocio)
    score_service: Optional[ScoreService] = None
    momentum_service: Optional[MomentumService] = None
    heatmap_service: Optional[HeatmapService] = None
    indicator_service: Optional[IndicatorService] = None
    oportunidad_15m_service: Optional[Oportunidad15mService] = None
    bollinger_15m_service: Optional[Bollinger15mService] = None
    tendencia_15m_service: Optional[Tendencia15mService] = None
    precio_service: Optional[PrecioService] = None
    event_service: Optional[EventService] = None
    session_service: Optional[SessionService] = None
    health_service: Optional[HealthService] = None
    bar_15m_service: Optional[Bar15mService] = None
    screener_15m_service: Optional[Screener15mService] = None
    confluencia_service: Optional[ConfluenciaService] = None
    initial_balance_service: Optional[InitialBalanceService] = None
    sector_15m_service: Optional[Sector15mService] = None
    divergencia_service: Optional[DivergenciaService] = None
    divergencia_5m_service: Optional[Divergencia5mService] = None
    vwap_ib_service: Optional[VwapIbService] = None

    name: str = field(default="container")

    # ── construcción ────────────────────────────────────────────────────────
    @classmethod
    def build(cls, settings: Optional[Settings] = None, connect: bool = False) -> "Container":
        settings = settings or get_settings()
        connector: Optional[PostgreSQLConnector] = None
        if settings.db_configurada:
            connector = PostgreSQLConnector(**settings.db_kwargs())
            if connect:
                connector.connect()

        container = cls(settings=settings, connector=connector)
        container._wire()
        return container

    def _wire(self) -> None:
        self.latest_tick_repo = LatestTickRepository(self.connector)
        self.score_repo = ScoreRepository(self.connector)
        self.heatmap_repo = HeatmapRepository(self.connector)
        self.events_repo = EventsRepository(self.connector)
        self.series_repo = SeriesRepository(self.connector)
        self.indicator_repo = IndicatorTfRepository(self.connector)
        self.session_repo = SessionRepository(self.connector)
        self.bar_repo = Bar15mRepository(self.connector)

        self.score_service = ScoreService(
            latest_tick_repo=self.latest_tick_repo,
            heatmap_repo=self.heatmap_repo,
            indicator_repo=self.indicator_repo,
            series_repo=self.series_repo,
            settings=self.settings,
        )
        self.momentum_service = MomentumService(self.latest_tick_repo, self.settings)
        self.heatmap_service = HeatmapService(self.heatmap_repo, self.settings)
        self.indicator_service = IndicatorService(
            self.latest_tick_repo, self.indicator_repo, self.settings
        )
        self.oportunidad_15m_service = Oportunidad15mService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.bollinger_15m_service = Bollinger15mService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.tendencia_15m_service = Tendencia15mService(
            self.bollinger_15m_service, self.latest_tick_repo, self.settings
        )
        self.precio_service = PrecioService(
            self.series_repo, self.score_service, self.settings
        )
        self.event_service = EventService(self.events_repo, self.settings)
        self.session_service = SessionService(self.session_repo, self.settings)
        self.health_service = HealthService(
            self.settings,
            self.latest_tick_repo,
            self.heatmap_repo,
            self.events_repo,
            self.indicator_repo,
        )
        self.bar_15m_service = Bar15mService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.screener_15m_service = Screener15mService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.confluencia_service = ConfluenciaService(
            self.indicator_repo, self.latest_tick_repo, self.settings
        )
        self.initial_balance_service = InitialBalanceService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.sector_15m_service = Sector15mService(
            self.screener_15m_service, self.latest_tick_repo, self.settings
        )
        self.divergencia_service = DivergenciaService(self.bar_repo, self.settings)
        self.divergencia_5m_service = Divergencia5mService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )
        self.vwap_ib_service = VwapIbService(
            self.bar_repo, self.latest_tick_repo, self.settings
        )

    # ── utilidades ──────────────────────────────────────────────────────────
    def logger(self, name: str) -> logging.Logger:
        return get_logger(name)

    @property
    def db_habilitada(self) -> bool:
        return self.connector is not None

    def close(self) -> None:
        if self.connector is not None:
            self.connector.disconnect()

    def __enter__(self) -> "Container":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
